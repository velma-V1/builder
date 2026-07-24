# Project Baseline Manifest — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01I §3.3` (versioned multi-repository baseline). Machine schema: `schemas/manifests/project-baseline-manifest-v1.schema.json` (PH-5).

## Required contents (`01I §3.3`)
```yaml
project_id:            PROJ-...
primary_repository:    <canonical identity>
repositories:
  - { canonical_identity, approved_commit }
  - ...
dependency_relationships: [ ordering / edges ]
submodules:            [ ... ]
git_lfs_objects:       [ ... ]
version_constraints:   [ compatible constraints ]
release_artifact_hashes: { ... }   # when applicable
promotion_mode:        independent | atomic
```

## Rules
- A combined project/integration/release cannot be verified solely because each repository passes independently; the declared cross-repository compatibility and promotion mode must also pass (`01I §3.3`).
- Versioned; consumed by the Git/workspace manager, Promotion Package, and release plan.
