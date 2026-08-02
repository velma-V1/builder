"""Immutable evidence/manifest models for Phase 3B's independent Verification Engine.

Distinct from every other "evidence"-adjacent shape in this codebase: not
``factory.integrations.agent_zero.models.EvidenceBundle`` (the untrusted worker-self-reported
bundle -- input to this package, never trusted directly) and not a Builder-authoritative record on
its own until persisted by ``engine.py`` into ``evidence_packages``/``promotion_manifests``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One independently-produced verification finding. ``passed`` is this item's own verdict --
    never the worker's self-report."""

    kind: str
    detail: str
    passed: bool


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    """An immutable record of every independent check run against one worker run's output."""

    task_id: str
    run_id: str
    items: tuple[EvidenceItem, ...]
    created_at: str

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.items)

    def digest(self) -> str:
        return hashlib.sha256(evidence_package_canonical(self).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ManifestFile:
    path: str
    content_digest: str


@dataclass(frozen=True, slots=True)
class PromotionManifest:
    """The exact, immutable set of files a verified run is permitted to promote -- nothing
    outside this manifest may ever be applied to the live repository during promotion."""

    task_id: str
    run_id: str
    branch_ref: str
    base_sha: str
    files: tuple[ManifestFile, ...]
    created_at: str

    def digest(self) -> str:
        return hashlib.sha256(promotion_manifest_canonical(self).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def evidence_package_json(package: EvidencePackage) -> str:
    """Serialize only the versioned persistence schema, never dataclass internals."""
    return _canonical_json(
        {
            "schema_version": 1,
            "items": [
                {"kind": item.kind, "detail": item.detail, "passed": item.passed}
                for item in package.items
            ],
        }
    )


def evidence_package_canonical(package: EvidencePackage) -> str:
    return _canonical_json(
        {
            "task_id": package.task_id,
            "run_id": package.run_id,
            "created_at": package.created_at,
            "payload": json.loads(evidence_package_json(package)),
        }
    )


def promotion_manifest_json(manifest: PromotionManifest) -> str:
    """Serialize only the versioned persistence schema, never dataclass internals."""
    return _canonical_json(
        {
            "schema_version": 1,
            "files": [
                {"path": item.path, "content_digest": item.content_digest}
                for item in manifest.files
            ],
        }
    )


def promotion_manifest_canonical(manifest: PromotionManifest) -> str:
    return _canonical_json(
        {
            "task_id": manifest.task_id,
            "run_id": manifest.run_id,
            "branch_ref": manifest.branch_ref,
            "base_sha": manifest.base_sha,
            "created_at": manifest.created_at,
            "payload": json.loads(promotion_manifest_json(manifest)),
        }
    )
