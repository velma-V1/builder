"""Python interpreter classification + linked-SQLite detection (preinstall preparation).

The SQLite version that matters is the one linked by the **exact interpreter that runs the factory**
— never the ``sqlite3`` CLI. This module classifies how that interpreter is provided (uv-managed,
distro, or custom) so the correct Option-A remediation path can be selected, and reports the linked
engine version. Classification is a pure function over path strings so it is deterministic and
unit-tested; the live reading uses the running interpreter.
"""

from __future__ import annotations

import sqlite3
import sys
from enum import StrEnum


class PythonKind(StrEnum):
    UV_MANAGED = "uv_managed"
    DISTRO = "distro"
    CUSTOM = "custom"


# Markers that identify a uv-managed standalone interpreter (python-build-standalone under uv).
_UV_MARKERS = (
    "/uv/python", "/uv/tools", "\\uv\\python", "share/uv/python", "python-build-standalone",
)
# Distro interpreters live under the system prefixes.
_DISTRO_PREFIXES = ("/usr/bin/", "/usr/local/bin/", "/bin/", "/usr/lib/")


def classify_python(executable: str, base_prefix: str = "") -> PythonKind:
    """Classify an interpreter as uv-managed, distro, or custom from its path(s).

    ``executable`` is ``sys.executable``; ``base_prefix`` is ``sys.base_prefix`` (optional). The
    check is conservative: uv markers win first, then distro prefixes, else ``CUSTOM``.
    """
    haystack = f"{executable}\n{base_prefix}".lower()
    if any(marker in haystack for marker in _UV_MARKERS):
        return PythonKind.UV_MANAGED
    if any(executable.startswith(prefix) for prefix in _DISTRO_PREFIXES):
        return PythonKind.DISTRO
    return PythonKind.CUSTOM


_REMEDIATION: dict[PythonKind, str] = {
    PythonKind.UV_MANAGED: (
        "uv-managed interpreters bundle their own SQLite; an OS libsqlite3 upgrade does NOT move "
        "the linked version. Preferred: rebuild the environment on a uv Python whose build already "
        "links SQLite >= 3.51.3 (or a system Python that does), then `uv sync` to rebuild the env. "
        "LD_PRELOAD is a last resort and does not override a statically linked engine."
    ),
    PythonKind.DISTRO: (
        "distro interpreters dynamically link the OS libsqlite3; upgrade libsqlite3 via the "
        "approved package source so the same interpreter picks up >= 3.51.3 (verify with the "
        "factory interpreter, not the CLI)."
    ),
    PythonKind.CUSTOM: (
        "custom interpreter: determine its SQLite linkage explicitly; if static, rebuild "
        "the interpreter/extension against SQLite >= 3.51.3. Verify with the factory interpreter."
    ),
}


def remediation_note(kind: PythonKind) -> str:
    return _REMEDIATION[kind]


def linked_sqlite_version() -> tuple[int, int, int]:
    """The SQLite version linked by the *running* interpreter (authoritative for compliance)."""
    parts = sqlite3.sqlite_version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def running_interpreter() -> tuple[PythonKind, str]:
    """Classify the running interpreter and return ``(kind, sys.executable)``."""
    return classify_python(sys.executable, sys.base_prefix), sys.executable
