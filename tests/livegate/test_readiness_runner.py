"""Stage-3 — readiness runner: unavailable / timeout / malformed / pass-fail aggregation."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "run_readiness_under_test", ROOT / "scripts" / "live_gate" / "run_readiness.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner: Any = _load_runner()


def test_absent_binary_is_unavailable() -> None:
    assert runner._read_only_command(["definitely-not-a-real-binary-xyz-123"]) is None


def test_timeout_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: object, **_k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="x", timeout=1)

    monkeypatch.setattr(runner.shutil, "which", lambda _n: "/bin/true")
    monkeypatch.setattr(runner.subprocess, "run", _boom)
    assert runner._read_only_command(["anything"]) is None


def test_os_error_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    def _oserr(*_a: object, **_k: object) -> object:
        raise OSError("boom")

    monkeypatch.setattr(runner.shutil, "which", lambda _n: "/bin/true")
    monkeypatch.setattr(runner.subprocess, "run", _oserr)
    assert runner._read_only_command(["anything"]) is None


def test_build_report_puts_sqlite_first_and_is_not_ready_below_floor() -> None:
    report = runner.build_report()
    assert report.checks[0].check_id == "sqlite-engine-floor"
    # This environment links SQLite 3.50.4 (below floor) → mandatory FAIL → not ready.
    assert not report.ready
    assert any(c.check_id == "sqlite-engine-floor" for c in report.blocking_failures)
