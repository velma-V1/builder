"""One-command Builder launcher (Phase 3A).

Starts, health-checks, and cleanly stops the three required Phase 3A services: the read-only
API, the write-authorized orchestrator API, and the Vite dashboard. Docker and Ollama are
optionally detected and reported but never block startup or the dashboard opening -- Phase 3A
does not use either.

All-or-nothing: if any required service fails to become healthy, every already-started process
is terminated (each in its own process group, so a spawned grandchild -- e.g. Vite's own `node`
child process -- is also killed, not just the direct child) and the launcher exits non-zero.
The same cleanup runs on Ctrl-C/SIGTERM, and if any service later exits unexpectedly.

Neither ``run_api.py`` nor ``run_orchestrator.py`` ever applies migrations itself; this script
runs the explicit setup step first, exactly like a human operator would.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import BuilderConfig, load_config

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEALTH_TIMEOUT_S = 30.0
_HEALTH_POLL_INTERVAL_S = 0.5
_REQUIRED_EXECUTABLES = ("python3", "node", "npm")
_OPTIONAL_EXECUTABLES = (("Docker", "docker"), ("Ollama", "ollama"))


class StartupFailure(Exception):
    """Raised to trigger the all-or-nothing cleanup path; never leaks internals to stdout."""


def _is_windows() -> bool:
    return sys.platform == "win32"


def _creation_flags() -> int:
    """Return the Windows process-group flag without importing a platform-only name."""
    if not _is_windows():
        return 0
    flag = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", None)
    if not isinstance(flag, int):
        raise StartupFailure("Windows subprocess support lacks CREATE_NEW_PROCESS_GROUP")
    return flag


def check_required_dependencies(config: BuilderConfig) -> list[str]:
    """Everything Phase 3A actually needs. Returns a list of problems -- empty means all good."""
    problems: list[str] = []
    if not config.repository_path.exists():
        problems.append(f"repository path not found: {config.repository_path}")
    for exe in _REQUIRED_EXECUTABLES:
        if shutil.which(exe) is None:
            problems.append(f"required executable not found on PATH: {exe}")
    for name, port in (
        ("read API", config.read_api_port),
        ("orchestrator API", config.orchestrator_api_port),
        ("dashboard", config.dashboard_port),
    ):
        if port_in_use(port):
            problems.append(f"required port already in use for {name}: {port}")
    return problems


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def report_optional_dependencies() -> None:
    """Docker/Ollama: detected and reported, never gated on -- Phase 3A doesn't use either."""
    for name, executable in _OPTIONAL_EXECUTABLES:
        path = shutil.which(executable)
        status = f"found ({path})" if path else "not found (optional -- unused by Phase 3A)"
        print(f"[start_all] {name}: {status}")


def spawn(
    cmd: Sequence[str], *, cwd: Path, log_path: Path, env: Mapping[str, str] | None = None
) -> subprocess.Popen[bytes]:
    """Start a subprocess in its own process group/session, so a grandchild it spawns (e.g.
    Vite's own ``node`` child) is also reachable by ``terminate_process_group`` later."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("wb")
    return subprocess.Popen(  # noqa: S603 - cmd is a fixed, code-defined argv, not shell-parsed
        list(cmd),
        cwd=str(cwd),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=None if env is None else {**os.environ, **env},
        creationflags=_creation_flags(),
        start_new_session=not _is_windows(),
    )


def terminate_process_group(proc: subprocess.Popen[bytes]) -> None:
    """Kill a process and everything in its process group (a grandchild included), verifying
    it's actually gone -- never leaves an orphan behind on a normal Ctrl-C/shutdown path."""
    if proc.poll() is not None:
        return
    if _is_windows():
        taskkill = Path(os.environ["SYSTEMROOT"]) / "System32" / "taskkill.exe"
        try:
            result = subprocess.run(  # noqa: S603 -- fixed system executable and numeric child PID
                [str(taskkill), "/PID", str(proc.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired as exc:
            raise StartupFailure(f"taskkill timed out for process tree {proc.pid}") from exc
        if result.returncode != 0 and proc.poll() is None:
            raise StartupFailure(
                f"taskkill failed with exit code {result.returncode} for process tree {proc.pid}"
            )
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise StartupFailure(
                f"process tree {proc.pid} is still running after taskkill"
            ) from exc
        if proc.poll() is None:
            raise StartupFailure(f"process tree {proc.pid} is still running after taskkill")
        return

    with contextlib.suppress(ProcessLookupError):
        subprocess.run(  # noqa: S603 -- fixed executable and numeric process-group ID
            ["/bin/kill", "--", f"-{proc.pid}"], check=False, capture_output=True
        )
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            subprocess.run(  # noqa: S603 -- fixed executable and numeric process-group ID
                ["/bin/kill", "-KILL", "--", f"-{proc.pid}"], check=False, capture_output=True
            )
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)


def wait_healthy(
    name: str, health_check: Callable[[], bool], *, timeout_s: float = _HEALTH_TIMEOUT_S
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if health_check():
            print(f"[start_all] {name}: healthy")
            return
        time.sleep(_HEALTH_POLL_INTERVAL_S)
    raise StartupFailure(f"{name} did not become healthy within {timeout_s:.0f}s")


def http_health_check(url: str) -> Callable[[], bool]:
    def _check() -> bool:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                return bool(response.status < 500)
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            return False

    return _check


@dataclass(frozen=True, slots=True)
class ServiceSpec:
    name: str
    cmd: tuple[str, ...]
    cwd: Path
    log_path: Path
    health_check: Callable[[], bool]
    env: Mapping[str, str] | None = None


def start_services(
    specs: Sequence[ServiceSpec], *, timeout_s: float = _HEALTH_TIMEOUT_S
) -> list[subprocess.Popen[bytes]]:
    """Start every service; on any health-check failure, terminate everything already started
    (all-or-nothing) and re-raise. Returns the running processes only on full success."""
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for spec in specs:
            processes.append(spawn(spec.cmd, cwd=spec.cwd, log_path=spec.log_path, env=spec.env))
        for spec in specs:
            wait_healthy(spec.name, spec.health_check, timeout_s=timeout_s)
    except StartupFailure:
        for proc in processes:
            terminate_process_group(proc)
        raise
    return processes


def _run_setup(config: BuilderConfig) -> bool:
    print("[start_all] running database setup...")
    result = subprocess.run(  # noqa: S603 - fixed, code-defined argv, not shell-parsed
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "setup_api_database.py"),
            "--database-path",
            str(config.database_path),
            "--security-database-path",
            str(config.database_path.with_name("security.db")),
            "--audit-database-path",
            str(config.database_path.with_name("audit.db")),
            "--integration-database-path",
            str(
                config.integrations.state_path
                if config.integrations is not None
                else config.repository_path / "integrations.db"
            ),
        ],
        cwd=str(_REPO_ROOT),
        check=False,
    )
    return result.returncode == 0


def _service_specs(
    config: BuilderConfig,
    log_dir: Path,
    operator_session_credential: str,
    agent_zero_credential: str,
    model_gateway_credential: str,
) -> tuple[ServiceSpec, ...]:
    integration_state_path = (
        config.integrations.state_path
        if config.integrations is not None
        else config.repository_path / "integrations.db"
    )
    return (
        ServiceSpec(
            name="read API",
            cmd=(
                sys.executable,
                str(_REPO_ROOT / "scripts" / "run_api.py"),
                "--database-path",
                str(config.database_path),
                "--port",
                str(config.read_api_port),
            ),
            cwd=_REPO_ROOT,
            log_path=log_dir / "read_api.log",
            health_check=http_health_check(
                f"http://127.0.0.1:{config.read_api_port}/api/tasks/snapshot?workstream=__health__"
            ),
        ),
        ServiceSpec(
            name="orchestrator API",
            cmd=(
                sys.executable,
                str(_REPO_ROOT / "scripts" / "run_orchestrator.py"),
                "--database-path",
                str(config.database_path),
                "--security-database-path",
                str(config.database_path.with_name("security.db")),
                "--audit-database-path",
                str(config.database_path.with_name("audit.db")),
                "--enable-worker",
                "--integration-state-path",
                str(integration_state_path),
                "--config-path",
                str(_REPO_ROOT / "config" / "builder.yaml"),
                "--port",
                str(config.orchestrator_api_port),
            ),
            cwd=_REPO_ROOT,
            log_path=log_dir / "orchestrator_api.log",
            health_check=http_health_check(
                f"http://127.0.0.1:{config.orchestrator_api_port}/api/orchestrator/health"
            ),
            env={
                "BUILDER_OPERATOR_SESSION_TOKEN": operator_session_credential,
                "BUILDER_AGENT_ZERO_API_KEY": agent_zero_credential,
                "BUILDER_MODEL_GATEWAY_TOKEN": model_gateway_credential,
                "OPENAI_API_KEY": model_gateway_credential,
                "AGENT_ZERO_MODEL": "devstral-small-2:24b",
                "AGENT_ZERO_PORT": str(config.integrations.agent_zero.port)
                if config.integrations
                else "50080",
                "WORLDMONITOR_PORT": str(config.integrations.worldmonitor.port)
                if config.integrations
                else "3000",
                "AGENT_ZERO_MEMORY": f"{config.integrations.agent_zero.memory_mb}m"
                if config.integrations
                else "4096m",
                "WORLDMONITOR_MEMORY": f"{config.integrations.worldmonitor.memory_mb}m"
                if config.integrations
                else "2048m",
                "AGENT_ZERO_CPUS": f"{config.integrations.agent_zero.cpu_millis / 1000:g}"
                if config.integrations
                else "2.0",
                "WORLDMONITOR_CPUS": f"{config.integrations.worldmonitor.cpu_millis / 1000:g}"
                if config.integrations
                else "1.0",
            },
        ),
        ServiceSpec(
            name="dashboard",
            cmd=(
                "npm",
                "run",
                "dev",
                "--",
                "--port",
                str(config.dashboard_port),
                "--strictPort",
            ),
            cwd=_REPO_ROOT / "ui",
            log_path=log_dir / "dashboard.log",
            health_check=http_health_check(f"http://127.0.0.1:{config.dashboard_port}/"),
            env={"BUILDER_OPERATOR_SESSION_TOKEN": operator_session_credential},
        ),
    )


def main() -> int:
    config = load_config()

    problems = check_required_dependencies(config)
    if problems:
        print("[start_all] cannot start -- required dependencies missing:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    report_optional_dependencies()

    if not _run_setup(config):
        print("[start_all] database setup failed; aborting.", file=sys.stderr)
        return 1

    log_dir = _REPO_ROOT / ".builder-logs"
    operator_session_credential = secrets.token_urlsafe(32)
    agent_zero_credential = secrets.token_urlsafe(32)
    model_gateway_credential = secrets.token_urlsafe(32)
    specs = _service_specs(
        config,
        log_dir,
        operator_session_credential,
        agent_zero_credential,
        model_gateway_credential,
    )

    try:
        processes = start_services(specs)
    except StartupFailure as exc:
        print(f"[start_all] {exc}", file=sys.stderr)
        return 1

    shutting_down = False

    def _shutdown(*_args: object) -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("[start_all] shutting down...")
        for proc in reversed(processes):
            terminate_process_group(proc)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    dashboard_url = f"http://127.0.0.1:{config.dashboard_port}/"
    print(f"[start_all] all services healthy. Dashboard: {dashboard_url}")
    if config.browser_auto_open:
        webbrowser.open(dashboard_url)
    print("[start_all] press Ctrl-C to stop all services.")

    while True:
        for proc in processes:
            if proc.poll() is not None:
                print(
                    f"[start_all] a required service exited unexpectedly (pid {proc.pid}); "
                    "stopping the others.",
                    file=sys.stderr,
                )
                for other in processes:
                    terminate_process_group(other)
                return 1
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
