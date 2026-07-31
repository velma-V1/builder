"""SHA-256-pinned durable-store schema templates (Stage-3, **unapplied**).

The durable execution/idempotency journal that PH-4/PH-6 will use in the live phase is defined as an
*unapplied* SQL template under ``deploy/schemas/durable``. It is **not** placed under
``migrations/`` (that directory has a frozen, hash-checked manifest) and it is **not** applied —
activation is gated behind the SQLite compliance gate and separate operator authorization.

This module pins each template's SHA-256 so review can detect any drift, and exposes a validator
that recomputes the on-disk hashes. Tests exercise the schema's idempotency/replay semantics against
a throwaway temporary database (the stdlib engine is fine for a test fixture); no durable store is
created.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

#: Repo-relative directory holding the unapplied durable schema templates.
DURABLE_SCHEMA_DIR = Path("deploy/schemas/durable")


@dataclass(frozen=True, slots=True)
class SchemaPin:
    filename: str
    sha256: str


#: Exact ordered manifest of durable schema templates and their pinned SHA-256 digests.
DURABLE_SCHEMA_MANIFEST: tuple[SchemaPin, ...] = (
    SchemaPin(
        "0001_execution_journal.sql",
        "849a33179c7a94f04655002aefcd6af31d719ca126e6edfff84b48c5a151410b",
    ),
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(root: Path) -> tuple[str, ...]:
    """Return mismatch descriptions for the durable schema manifest. Empty tuple ⇒ all pinned.

    Checks, for each declared template: the file exists and its SHA-256 matches the pin. Also flags
    any ``*.sql`` present in the directory that is not declared (undeclared drift).
    """
    schema_dir = root / DURABLE_SCHEMA_DIR
    problems: list[str] = []
    declared = {pin.filename for pin in DURABLE_SCHEMA_MANIFEST}
    for pin in DURABLE_SCHEMA_MANIFEST:
        target = schema_dir / pin.filename
        if not target.is_file():
            problems.append(f"missing: {pin.filename}")
            continue
        actual = sha256_of(target)
        if actual != pin.sha256:
            problems.append(
                f"hash mismatch: {pin.filename} (declared {pin.sha256}, actual {actual})"
            )
    if schema_dir.is_dir():
        for found in sorted(schema_dir.glob("*.sql")):
            if found.name not in declared:
                problems.append(f"undeclared: {found.name}")
    return tuple(problems)
