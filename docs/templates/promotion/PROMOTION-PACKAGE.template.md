# Promotion Package — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01E §3.8` (manifest), `01I §3.2` (Promotion Service), `01G` (ETM). Machine schema: `schemas/manifests/promotion-package-v1.schema.json` (PH-5/PH-7).
**Rule:** a package with missing, ambiguous, stale, or hash-mismatched contents is **blocked** (`01E §3.8`). Only the Promotion Service may act on it (`01I §3.2`).

## Required contents (`01E §3.8`)
```yaml
identities:           { project_id, task_id, stage, workstream_id, lane_id, sandbox_id }
source:               { repository_identity, approved_source_commit, task_branch, checkout_identity }
environment:          { base_image, runtime, tool_versions, model_versions, dependency_versions }
changes:              { added: [...], modified: [...], deleted: [...], renamed: [...], generated: [...] }
hashes:               { staged_files: {...}, promoted_artifacts: {...} }
diff_and_scope:       { complete_diff, scope_comparison_vs_approved }
dependency_changes:   { dependencies, lockfiles, models, images, schemas, migrations, configuration }
verification:         <link to Evidence Traceability Manifest>   # 01G
policy_results:       { security, path, secret, license, resource, policy }
unresolved:           { risks, limitations, non_promotable_items }
approval:             { approver_identity, approval_record_reference }
recovery:             { checkpoint_reference, rollback_reference }
staging:              { staging_area_identity, integrity_status }
```

## Rules
- Secrets are excluded from the package (`01E §3.4`).
- Multi-repository promotions require a `CTR-BASELINE-MANIFEST` and its declared cross-repo compatibility to pass (`01I §3.3`).
