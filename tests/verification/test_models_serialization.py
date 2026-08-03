from __future__ import annotations

from factory.verification.models import (
    EvidenceItem,
    EvidencePackage,
    ManifestFile,
    PromotionManifest,
    evidence_package_json,
    promotion_manifest_json,
)


def test_evidence_package_json_is_explicit_canonical_schema() -> None:
    package = EvidencePackage(
        task_id="task-1",
        run_id="run-1",
        items=(EvidenceItem(kind="scope", detail="clean", passed=True),),
        created_at="2026-08-02T00:00:00Z",
    )

    assert evidence_package_json(package) == (
        '{"items":[{"detail":"clean","kind":"scope","passed":true}],"schema_version":1}'
    )


def test_promotion_manifest_json_is_explicit_canonical_schema() -> None:
    manifest = PromotionManifest(
        task_id="task-1",
        run_id="run-1",
        branch_ref="factory/task-1",
        base_sha="abc",
        files=(ManifestFile(path="src/a.py", content_digest="def"),),
        created_at="2026-08-02T00:00:00Z",
    )

    assert promotion_manifest_json(manifest) == (
        '{"files":[{"content_digest":"def","path":"src/a.py"}],"schema_version":1}'
    )
