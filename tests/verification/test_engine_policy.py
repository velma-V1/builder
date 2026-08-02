from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.verification.engine import VerificationEngine


def test_missing_linter_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    monkeypatch.setattr("factory.verification.engine.shutil.which", lambda name: None)
    passed, detail = VerificationEngine._check_lint(object(), tmp_path, ("a.py",))
    assert not passed
    assert "required" in detail


def test_missing_type_checker_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    monkeypatch.setattr("factory.verification.engine.shutil.which", lambda name: None)
    passed, detail = VerificationEngine._check_types(object(), tmp_path, ("a.py",))
    assert not passed
    assert "required" in detail


def test_source_change_without_regression_test_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    passed, detail = VerificationEngine._check_tests(object(), tmp_path, ("a.py",))
    assert not passed
    assert "regression test" in detail


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
