"""Preinstall unit — source checksum manifest (SHA-256, drift detection)."""

from __future__ import annotations

from pathlib import Path

from factory.preinstall.source_manifest import (
    MANIFEST_PATH,
    MANIFEST_SOURCES,
    parse_manifest,
    render_manifest,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


def test_shipped_manifest_validates() -> None:
    assert validate_manifest(ROOT) == ()


def test_manifest_file_exists_and_covers_all_sources() -> None:
    declared = parse_manifest((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    assert set(declared) == set(MANIFEST_SOURCES)


def test_render_is_deterministic() -> None:
    assert render_manifest(ROOT) == render_manifest(ROOT)


def test_tamper_is_detected(tmp_path: Path) -> None:
    # Build a fake root with matching sources, then tamper one and re-validate.
    for rel in MANIFEST_SOURCES:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / rel).read_bytes())
    (tmp_path / MANIFEST_PATH).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / MANIFEST_PATH).write_text(render_manifest(tmp_path), encoding="utf-8")
    assert validate_manifest(tmp_path) == ()
    # Tamper one source:
    (tmp_path / MANIFEST_SOURCES[0]).write_text("# tampered\n", encoding="utf-8")
    assert any("hash mismatch" in p for p in validate_manifest(tmp_path))


def test_missing_manifest_reported(tmp_path: Path) -> None:
    assert any("missing manifest" in p for p in validate_manifest(tmp_path))
