from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.verification.engine import VerificationEngine
from factory.verification.execution import DockerIsolatedCommandRunner


class RecordingRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.calls: list[tuple[tuple[str, ...], Path, int]] = []

    def run(self, argv: tuple[str, ...], *, cwd: Path, timeout_s: int) -> SimpleNamespace:
        self.calls.append((argv, cwd, timeout_s))
        return SimpleNamespace(returncode=self.returncode, stdout="", stderr="")


def test_docker_runner_uses_hardened_networkless_ephemeral_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def _run(argv: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("factory.verification.execution.shutil.which", lambda name: "/bin/docker")
    monkeypatch.setattr("factory.verification.execution.subprocess.run", _run)
    (tmp_path / "test_output.py").write_text("def test_ok(): assert True\n")

    result = DockerIsolatedCommandRunner("builder-verifier:test").run(
        ("python", "-m", "pytest", "-q", "."), cwd=tmp_path, timeout_s=30
    )

    assert result.returncode == 0
    command = calls[0]
    assert "--network" in command and "none" in command
    assert "--read-only" in command
    assert "--cap-drop" in command and "ALL" in command
    assert "no-new-privileges" in command
    assert str(tmp_path) not in " ".join(command)


def test_missing_linter_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    engine = SimpleNamespace(command_runner=None)
    passed, detail = VerificationEngine._check_lint(engine, tmp_path, ("a.py",))
    assert not passed
    assert "required" in detail


def test_missing_type_checker_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    engine = SimpleNamespace(command_runner=None)
    passed, detail = VerificationEngine._check_types(engine, tmp_path, ("a.py",))
    assert not passed
    assert "required" in detail


def test_source_change_without_regression_test_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    engine = SimpleNamespace(command_runner=None)
    passed, detail = VerificationEngine._check_tests(engine, tmp_path, ("a.py",))
    assert not passed
    assert "regression test" in detail


def test_worker_controlled_tests_require_an_isolated_runner(tmp_path: Path) -> None:
    (tmp_path / "test_output.py").write_text("def test_ok(): assert True\n")
    engine = SimpleNamespace(command_runner=None)

    passed, detail = VerificationEngine._check_tests(engine, tmp_path, ("test_output.py",))

    assert not passed
    assert "isolated" in detail


def test_test_command_is_delegated_to_the_isolated_runner(tmp_path: Path) -> None:
    (tmp_path / "test_output.py").write_text("def test_ok(): assert True\n")
    runner = RecordingRunner()
    engine = SimpleNamespace(command_runner=runner)

    passed, detail = VerificationEngine._check_tests(engine, tmp_path, ("test_output.py",))

    assert passed
    assert detail == "tests passed in isolated sandbox"
    assert runner.calls == [
        (("python", "-m", "pytest", "-q", "."), tmp_path, 60),
    ]


def test_plain_text_acceptance_is_rejected_not_substring_matched(tmp_path: Path) -> None:
    (tmp_path / "result.txt").write_text("the expected phrase")
    reader = SimpleNamespace(
        get_task_request=lambda task_id: SimpleNamespace(expected_result="expected phrase")
    )
    engine = SimpleNamespace(orchestrator_reader=reader)
    passed, detail = VerificationEngine._check_acceptance(
        engine, "task-1", tmp_path, ("result.txt",), direct_read_only=False
    )
    assert not passed
    assert "JSON object" in detail


def test_structured_acceptance_requires_exact_file_digest(tmp_path: Path) -> None:
    output = tmp_path / "result.txt"
    output.write_text("complete")
    import hashlib

    criteria = json.dumps(
        {
            "required_files": ["result.txt"],
            "required_sha256": {"result.txt": hashlib.sha256(output.read_bytes()).hexdigest()},
        }
    )
    reader = SimpleNamespace(
        get_task_request=lambda task_id: SimpleNamespace(expected_result=criteria)
    )
    engine = SimpleNamespace(orchestrator_reader=reader)
    passed, _ = VerificationEngine._check_acceptance(
        engine, "task-1", tmp_path, ("result.txt",), direct_read_only=False
    )
    assert passed


def test_direct_read_only_cannot_bypass_supplied_acceptance(tmp_path: Path) -> None:
    reader = SimpleNamespace(
        get_task_request=lambda task_id: SimpleNamespace(expected_result='{"required_files":[]}')
    )
    engine = SimpleNamespace(orchestrator_reader=reader)
    passed, detail = VerificationEngine._check_acceptance(
        engine, "task-1", tmp_path, (), direct_read_only=True
    )
    assert not passed
    assert "DIRECT_READ_ONLY" in detail
