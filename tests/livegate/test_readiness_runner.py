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


def test_decode_console_bytes_plain_utf8() -> None:
    assert runner._decode_console_bytes(b"Default Version: 2") == "Default Version: 2"


def test_decode_console_bytes_utf16le_with_bom() -> None:
    raw = "Default Version: 2".encode("utf-16-le")
    assert runner._decode_console_bytes(b"\xff\xfe" + raw) == "Default Version: 2"


def test_decode_console_bytes_utf16le_without_bom() -> None:
    # wsl.exe frequently emits BOM-less UTF-16LE; the NUL-density heuristic must still recover it.
    raw = "Default Version: 2".encode("utf-16-le")
    assert runner._decode_console_bytes(raw) == "Default Version: 2"


def test_decode_console_bytes_utf8_bom() -> None:
    decoded = runner._decode_console_bytes(b"\xef\xbb\xbfDocker version 24.0.7")
    assert decoded == "Docker version 24.0.7"


def test_decode_console_bytes_empty() -> None:
    assert runner._decode_console_bytes(b"") == ""


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


def test_build_report_puts_sqlite_first() -> None:
    # Ordering must hold regardless of which SQLite engine happens to be linked in this environment.
    report = runner.build_report()
    assert report.checks[0].check_id == "sqlite-engine-floor"


def test_build_report_is_not_ready_when_sqlite_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    # Do not assume the ambient interpreter links a below-floor SQLite (it may not, e.g. on a newer
    # Python/OS build) — inject a fixed below-floor version, mirroring
    # durable_activation_fails_closed_below_floor's own below_floor_version parameter.
    below_floor_version = (3, 50, 4)
    original_evaluate = runner.evaluate_sqlite_compliance
    monkeypatch.setattr(
        runner,
        "evaluate_sqlite_compliance",
        lambda: original_evaluate(version=below_floor_version),
    )
    report = runner.build_report()
    assert report.checks[0].check_id == "sqlite-engine-floor"
    assert not report.ready
    assert any(c.check_id == "sqlite-engine-floor" for c in report.blocking_failures)


def test_build_report_is_ready_for_sqlite_when_at_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    # Symmetric case: an engine that meets the floor must not block readiness on this gate.
    original_evaluate = runner.evaluate_sqlite_compliance
    monkeypatch.setattr(
        runner,
        "evaluate_sqlite_compliance",
        lambda: original_evaluate(version=(3, 51, 3)),
    )
    report = runner.build_report()
    assert not any(c.check_id == "sqlite-engine-floor" for c in report.blocking_failures)
