"""Source checksum manifest for the preinstall package (SHA-256, deterministic).

Pins the SHA-256 of the preinstall/livegate source so review can detect any drift in the code that
will drive live installation. The manifest lives at ``deploy/preinstall/source-checksums.sha256`` in
the standard ``<sha256>  <path>`` format (the same format ``sha256sum`` emits/accepts), so it can
be regenerated and re-validated deterministically. This is repository-internal integrity — distinct
from the SQLite *download* verification, which uses the vendor's SHA3-256 (see docs/live-gate/10).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

MANIFEST_PATH = Path("deploy/preinstall/source-checksums.sha256")

#: Files whose integrity the manifest pins (relative to repo root), sorted for determinism.
MANIFEST_SOURCES: tuple[str, ...] = (
    "src/factory/livegate/acceptance.py",
    "src/factory/livegate/adapter_contracts.py",
    "src/factory/livegate/compose_topology.py",
    "src/factory/livegate/durable_schema.py",
    "src/factory/livegate/models.py",
    "src/factory/livegate/redaction.py",
    "src/factory/livegate/sqlite_compliance.py",
    "src/factory/livegate/version_probe.py",
    "src/factory/preinstall/installer.py",
    "src/factory/preinstall/network_policy.py",
    "src/factory/preinstall/phase_order.py",
    "src/factory/preinstall/prerequisites.py",
    "src/factory/preinstall/python_env.py",
    "src/factory/preinstall/rollback.py",
    "src/factory/preinstall/source_manifest.py",
    "deploy/schemas/durable/0001_execution_journal.sql",
    "deploy/compose/factory-workers.compose.yaml",
    "deploy/compose/factory-broker.compose.yaml",
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_manifest(root: Path) -> str:
    """Render the manifest text (``<sha256>  <path>`` lines) for the declared sources."""
    lines = [f"{sha256_of(root / rel)}  {rel}" for rel in MANIFEST_SOURCES]
    return "\n".join(lines) + "\n"


def parse_manifest(text: str) -> dict[str, str]:
    """Parse ``<sha256>  <path>`` lines into ``{path: sha256}`` (ignores blank lines)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        digest, _, path = stripped.partition("  ")
        out[path.strip()] = digest.strip()
    return out


def validate_manifest(root: Path) -> tuple[str, ...]:
    """Return mismatch/missing/undeclared descriptions. Empty ⇒ every source matches its pin."""
    manifest_file = root / MANIFEST_PATH
    if not manifest_file.is_file():
        return (f"missing manifest: {MANIFEST_PATH}",)
    declared = parse_manifest(manifest_file.read_text(encoding="utf-8"))
    problems: list[str] = []
    for rel in MANIFEST_SOURCES:
        target = root / rel
        if not target.is_file():
            problems.append(f"missing source: {rel}")
            continue
        actual = sha256_of(target)
        if declared.get(rel) != actual:
            problems.append(f"hash mismatch: {rel}")
    for path in declared:
        if path not in MANIFEST_SOURCES:
            problems.append(f"undeclared in code: {path}")
    return tuple(problems)
