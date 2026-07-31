"""Preinstall unit — interpreter classification + linked-SQLite detection."""

from __future__ import annotations

import sqlite3

import pytest

from factory.preinstall.python_env import (
    PythonKind,
    classify_python,
    linked_sqlite_version,
    remediation_note,
    running_interpreter,
)


@pytest.mark.parametrize(
    ("executable", "base_prefix", "expected"),
    [
        ("/home/u/.local/share/uv/python/cpython-3.12/bin/python3", "", PythonKind.UV_MANAGED),
        ("/root/project/.venv/bin/python", "/opt/uv/python/cpython-3.12", PythonKind.UV_MANAGED),
        ("/usr/bin/python3", "/usr", PythonKind.DISTRO),
        ("/usr/local/bin/python3.12", "/usr/local", PythonKind.DISTRO),
        ("/opt/custom/py/bin/python", "/opt/custom/py", PythonKind.CUSTOM),
    ],
)
def test_classify_python(executable: str, base_prefix: str, expected: PythonKind) -> None:
    assert classify_python(executable, base_prefix) is expected


def test_remediation_note_present_for_each_kind() -> None:
    for kind in PythonKind:
        assert remediation_note(kind).strip()


def test_uv_note_warns_against_ld_preload_only() -> None:
    note = remediation_note(PythonKind.UV_MANAGED).lower()
    assert "ld_preload" in note and "last resort" in note


def test_linked_sqlite_matches_running_engine() -> None:
    assert linked_sqlite_version() == tuple(int(p) for p in sqlite3.sqlite_version.split("."))


def test_running_interpreter_returns_kind_and_path() -> None:
    kind, path = running_interpreter()
    assert isinstance(kind, PythonKind)
    assert path
