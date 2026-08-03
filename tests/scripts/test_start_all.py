"""Phase 3A — scripts/start_all.py: required-dependency checks, process-group spawn/cleanup,
and all-or-nothing service startup.

Uses real short-lived dummy processes (``python3 -c "..."``) rather than real uvicorn/npm, so
these tests stay fast and don't depend on a network stack -- the actual three-service path is
covered by the live end-to-end validation instead.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.worker_engine.support import loopback_unavailable_reason

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _is_windows() -> bool:
    return sys.platform == "win32"


def _load_script(name: str) -> ModuleType:
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses defined in this module (ServiceSpec, BuilderConfig) resolve their
    # `from __future__ import annotations` string annotations via sys.modules[__name__] at
    # class-definition time -- register before exec_module, or that lookup returns None.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _process_exists(pid: int) -> bool:
    if _is_windows():
        tasklist = Path(os.environ["SYSTEMROOT"]) / "System32" / "tasklist.exe"
        completed = subprocess.run(  # noqa: S603 -- fixed system executable and numeric PID
            [str(tasklist), "/FI", f"PID eq {pid}", "/NH"],
            check=False,
            capture_output=True,
            text=True,
        )
        return str(pid) in completed.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def start_all() -> ModuleType:
    return _load_script("start_all")


@pytest.fixture
def config(start_all: ModuleType, tmp_path: Path) -> Any:
    config_module = _load_script("_config")
    return config_module.BuilderConfig(
        wsl_distribution="Ubuntu",
        repository_path=tmp_path,
        database_path=tmp_path / "runtime.db",
        read_api_port=18000,
        orchestrator_api_port=18100,
        dashboard_port=11420,
        browser_auto_open=False,
    )


# ---- required vs. optional dependency checks -------------------------------------------


@pytest.mark.loopback
def test_check_required_dependencies_passes_when_everything_present(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    assert start_all.check_required_dependencies(config) == []


@pytest.mark.loopback
def test_check_required_dependencies_reports_missing_repository_path(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    bad_config = dataclasses.replace(config, repository_path=Path("/no/such/dir"))
    problems = start_all.check_required_dependencies(bad_config)
    assert any("repository path not found" in p for p in problems)


@pytest.mark.loopback
def test_check_required_dependencies_reports_missing_executable(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all.shutil, "which", lambda exe: None if exe == "npm" else "/bin/x")
    problems = start_all.check_required_dependencies(config)
    assert any("npm" in p for p in problems)


@pytest.mark.loopback
def test_check_required_dependencies_reports_port_already_in_use(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", config.read_api_port))
    server.listen(1)
    try:
        problems = start_all.check_required_dependencies(config)
        assert any(str(config.read_api_port) in p for p in problems)
    finally:
        server.close()


@pytest.mark.loopback
def test_port_in_use_detects_a_free_port_as_free(start_all: ModuleType) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
    assert start_all.port_in_use(free_port) is False


@pytest.mark.loopback
def test_docker_ollama_are_reported_but_never_required(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate neither being installed -- must not appear anywhere in the required-deps list.
    monkeypatch.setattr(
        start_all.shutil,
        "which",
        lambda exe: None if exe in ("docker", "ollama") else f"/usr/bin/{exe}",
    )
    problems = start_all.check_required_dependencies(config)
    assert not any("docker" in p.lower() or "ollama" in p.lower() for p in problems)
    start_all.report_optional_dependencies()  # must not raise


# ---- process-group spawn / cleanup (the Vite-grandchild lesson) ------------------------


def test_windows_creation_flags_uses_guarded_platform_lookup(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.setattr(start_all.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)

    assert start_all._creation_flags() == 0x200


def test_creation_flags_does_not_require_windows_constant_on_linux(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: False)
    monkeypatch.delattr(start_all.subprocess, "CREATE_NEW_PROCESS_GROUP", raising=False)

    assert start_all._creation_flags() == 0


def test_windows_creation_flags_fail_closed_when_constant_is_unavailable(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.delattr(start_all.subprocess, "CREATE_NEW_PROCESS_GROUP", raising=False)

    with pytest.raises(start_all.StartupFailure, match="CREATE_NEW_PROCESS_GROUP"):
        start_all._creation_flags()


class _FakeWindowsProcess:
    pid = 123

    def __init__(self, *, exits_on_wait: bool = True) -> None:
        self.exited = False
        self.exits_on_wait = exits_on_wait

    def poll(self) -> int | None:
        return 0 if self.exited else None

    def wait(self, timeout: float) -> int:
        if self.exits_on_wait:
            self.exited = True
        return 0


def test_windows_cleanup_times_out_boundedly(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    monkeypatch.setattr(
        start_all.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("taskkill", 5)),
    )

    with pytest.raises(start_all.StartupFailure, match="taskkill timed out"):
        start_all.terminate_process_group(_FakeWindowsProcess())


def test_windows_cleanup_rejects_failed_taskkill(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    monkeypatch.setattr(
        start_all.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 1})(),
    )

    with pytest.raises(start_all.StartupFailure, match="taskkill failed"):
        start_all.terminate_process_group(_FakeWindowsProcess())


def test_windows_cleanup_requires_verified_process_exit(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    monkeypatch.setattr(
        start_all.subprocess,
        "run",
        lambda *_args, **_kwargs: type("Completed", (), {"returncode": 0})(),
    )

    with pytest.raises(start_all.StartupFailure, match="still running"):
        start_all.terminate_process_group(_FakeWindowsProcess(exits_on_wait=False))


def test_windows_cleanup_succeeds_only_after_verified_exit(
    start_all: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(start_all, "_is_windows", lambda: True)
    monkeypatch.setenv("SYSTEMROOT", "C:/Windows")
    timeouts: list[float] = []

    def _run(*_args: object, **kwargs: object) -> Any:
        timeouts.append(float(kwargs["timeout"]))
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(start_all.subprocess, "run", _run)
    proc = _FakeWindowsProcess()

    start_all.terminate_process_group(proc)

    assert proc.poll() == 0
    assert timeouts == [5]


def test_phase3b_service_specs_inject_complete_runtime_configuration(
    start_all: ModuleType, config: Any, tmp_path: Path
) -> None:
    specs = start_all._service_specs(
        config, tmp_path / "logs", "session-secret", "agent-zero-secret", "gateway-secret"
    )
    orchestrator = next(spec for spec in specs if spec.name == "orchestrator API")
    dashboard = next(spec for spec in specs if spec.name == "dashboard")

    assert "--security-database-path" in orchestrator.cmd
    assert "--audit-database-path" in orchestrator.cmd
    assert "--enable-worker" in orchestrator.cmd
    assert orchestrator.env == {
        "BUILDER_OPERATOR_SESSION_TOKEN": "session-secret",
        "BUILDER_AGENT_ZERO_API_KEY": "agent-zero-secret",
        "BUILDER_MODEL_GATEWAY_TOKEN": "gateway-secret",
        "OPENAI_API_KEY": "gateway-secret",
        "AGENT_ZERO_MODEL": "devstral-small-2:24b",
        "AGENT_ZERO_PORT": "50080",
        "WORLDMONITOR_PORT": "3000",
        "AGENT_ZERO_MEMORY": "4096m",
        "WORLDMONITOR_MEMORY": "2048m",
        "AGENT_ZERO_CPUS": "2.0",
        "WORLDMONITOR_CPUS": "1.0",
    }
    assert dashboard.env == {"BUILDER_OPERATOR_SESSION_TOKEN": "session-secret"}
    assert not any(name.startswith("VITE_") for name in dashboard.env)


def test_dashboard_credential_is_proxy_scoped_not_browser_injected() -> None:
    root = Path(__file__).resolve().parents[2]
    main_source = (root / "ui/src/main.tsx").read_text(encoding="utf-8")
    api_source = (root / "ui/src/api/orchestrator.ts").read_text(encoding="utf-8")
    proxy_source = (root / "ui/vite.config.ts").read_text(encoding="utf-8")

    assert "VITE_OPERATOR_SESSION_TOKEN" not in main_source + api_source + proxy_source
    assert "BUILDER_OPERATOR_SESSION_TOKEN" in proxy_source
    assert "Authorization" not in api_source


def test_database_setup_includes_security_and_audit_schemas(
    start_all: ModuleType, config: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[str] = []

    def _run(argv: list[str], **_kwargs: object) -> Any:
        captured.extend(argv)
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(start_all.subprocess, "run", _run)

    assert start_all._run_setup(config)
    assert "--security-database-path" in captured
    assert "--audit-database-path" in captured


def test_spawn_and_terminate_process_group_kills_the_process(
    start_all: ModuleType, tmp_path: Path
) -> None:
    proc = start_all.spawn(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        log_path=tmp_path / "logs" / "a.log",
    )
    assert proc.poll() is None
    start_all.terminate_process_group(proc)
    assert proc.poll() is not None


def test_terminate_process_group_also_kills_a_spawned_grandchild(
    start_all: ModuleType, tmp_path: Path
) -> None:
    # The parent immediately spawns a detached child of its own (mirrors npm -> vite) and writes
    # the grandchild's PID to a file so the test can confirm it's actually gone afterward.
    pid_file = tmp_path / "grandchild.pid"
    script = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    proc = start_all.spawn(
        [sys.executable, "-c", script], cwd=tmp_path, log_path=tmp_path / "logs" / "b.log"
    )

    deadline = time.monotonic() + 5
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pid_file.exists(), "grandchild never reported its PID"
    grandchild_pid = int(pid_file.read_text())

    start_all.terminate_process_group(proc)

    # The grandchild must be gone too -- killing only the direct child would leave it orphaned.
    time.sleep(0.2)
    assert not _process_exists(grandchild_pid)


def test_terminate_process_group_on_an_already_exited_process_is_a_no_op(
    start_all: ModuleType, tmp_path: Path
) -> None:
    proc = start_all.spawn(
        [sys.executable, "-c", "pass"], cwd=tmp_path, log_path=tmp_path / "logs" / "c.log"
    )
    proc.wait(timeout=5)
    start_all.terminate_process_group(proc)  # must not raise


# ---- all-or-nothing startup -------------------------------------------------------------


def test_start_services_returns_processes_when_all_become_healthy(
    start_all: ModuleType, tmp_path: Path
) -> None:
    specs = [
        start_all.ServiceSpec(
            name="ok-service",
            cmd=(sys.executable, "-c", "import time; time.sleep(60)"),
            cwd=tmp_path,
            log_path=tmp_path / "logs" / "ok.log",
            health_check=lambda: True,
        )
    ]
    processes = start_all.start_services(specs, timeout_s=2)
    assert len(processes) == 1
    assert processes[0].poll() is None
    start_all.terminate_process_group(processes[0])


def test_start_services_is_all_or_nothing_on_a_failed_health_check(
    start_all: ModuleType, tmp_path: Path
) -> None:
    pid_file = tmp_path / "good.pid"
    specs = [
        start_all.ServiceSpec(
            name="good-service",
            cmd=(
                sys.executable,
                "-c",
                f"import os; open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
                "import time; time.sleep(60)",
            ),
            cwd=tmp_path,
            log_path=tmp_path / "logs" / "good.log",
            health_check=lambda: True,
        ),
        start_all.ServiceSpec(
            name="bad-service",
            cmd=(sys.executable, "-c", "import time; time.sleep(60)"),
            cwd=tmp_path,
            log_path=tmp_path / "logs" / "bad.log",
            health_check=lambda: False,  # never becomes healthy
        ),
    ]

    with pytest.raises(start_all.StartupFailure):
        start_all.start_services(specs, timeout_s=1)

    # The good service, already healthy, must also have been torn down -- all-or-nothing.
    deadline = time.monotonic() + 5
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pid_file.exists()
    good_pid = int(pid_file.read_text())
    time.sleep(0.3)
    assert not _process_exists(good_pid)


def test_wait_healthy_raises_startup_failure_on_timeout(start_all: ModuleType) -> None:
    with pytest.raises(start_all.StartupFailure):
        start_all.wait_healthy("never-healthy", lambda: False, timeout_s=0.3)


def test_wait_healthy_returns_once_the_check_reports_true(start_all: ModuleType) -> None:
    calls = {"count": 0}

    def _check() -> bool:
        calls["count"] += 1
        return calls["count"] >= 3

    start_all.wait_healthy("eventually-healthy", _check, timeout_s=5)
    assert calls["count"] == 3


@pytest.fixture(autouse=True)
def _require_loopback_capability(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("loopback") is None:
        return
    reason = loopback_unavailable_reason()
    if reason is not None:
        pytest.skip(reason)
