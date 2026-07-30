# Component Specification — Safe File-Op Service (CMP-FILEOP)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T5) · **Governing:** `01K`
(§2.26-27/§3.1, acceptance #10/#11), `01R` Dec B (deletion approval-required). Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #40. **Added this pass (RPH3 Pass 4) via change-control:**
roadmap §PH-3 names "safe file-op" as a component and the section-3 plan owns `src/factory/fileops/**`, but the
prior 39-component map omitted a dedicated row — this corrects that omission. Baselines inherited; deltas only.

```yaml
component_id:          CMP-FILEOP
name:                  Safe File-Op Service
implementation_phase:  PH-3 (RPH3-T5)
responsibility: >
  The single safe path for file operations. Canonicalizes and validates every path before access and blocks
  every escape class (symlink, junction, reserved-name, path traversal, case-normalization, archive
  extraction). Enforces Decision B — ALL file deletion is approval-required — and applies archive limits
  (entry-count, nesting depth, decompressed size) to prevent archive bombs. Provides atomic, bounded write/
  read/move operations within the active task's owned+permitted paths.
non_responsibilities:
  - Does not decide base permissions (CMP-PERM) or approvals (CMP-APPROVAL) — it consumes their decisions.
  - Does not execute tools (CMP-TOOLGW) or provide the sandbox (PH-5).
  - Never deletes without a prior valid approval; never writes outside the granted path scope.
authoritative_state:   none for runtime state (R1); operates on the filesystem within granted scope; every
                       destructive/deletion op is audited (CMP-AUDITW).
inputs:
  - file operation request (op, raw path(s), task context)
  - canonical path authority + grant (CMP-PERM); deletion approval (CMP-APPROVAL) when applicable
outputs:
  - operation result (atomic success / rejection) with canonical path
  - escape/limit rejections raised as security events (audited)
interfaces:
  - "FileOpService.canonicalize(raw_path, ownership) -> CanonicalPath   # raises on any escape class"
  - "FileOpService.read(path) -> bytes                                   # within granted read scope"
  - "FileOpService.write_atomic(path, data) -> WriteResult               # bounded, atomic, in-scope"
  - "FileOpService.delete(path, approval_ref) -> DeleteResult            # REQUIRES valid CMP-APPROVAL (Dec B)"
  - "FileOpService.extract_archive(archive, dest, limits) -> ExtractResult  # entry/depth/size capped"
dependencies:
  - CMP-PERM (path authority + least-privilege grant + TOCTOU revalidation)
  - CMP-APPROVAL (mandatory for any delete; Dec B)
  - CMP-AUDITW (destructive/deletion operations audited)
owned_contracts:       [ ] (consumes CTR-PERMISSION-GRANT, CTR-APPROVAL-RECORD; defines no new contract)
permitted_authority:   BASE-P; file operations only within the active task's owned + permitted, canonicalized
                       paths, each within bounded size/file-count limits (01K §3.1).
prohibited_authority:  BASE-X + never deletes without approval (Dec B); never follows an escape out of scope;
                       never exceeds archive/decompression limits.
trust_boundary:        BASE-T; every raw path + archive is untrusted until canonicalized/validated; repository
                       or downloaded paths cannot widen scope.
failure_modes:
  - escape attempt (symlink/junction/reserved/traversal/case/archive) -> reject + security event
  - delete without valid approval -> denied (Dec B)
  - archive bomb (entry-count/depth/decompressed-size over cap) -> aborted
  - write outside granted scope -> denied
degradation_behavior:  BASE-D; path-authority failure fails closed (deny), never widens access.
recovery_behavior:     BASE-R; atomic writes leave no partial file; interrupted ops reconcile to a clean state.
security_requirements: BASE-S; path canonicalization + escape blocking + deletion approval-gating + archive
                       limits are core controls; violation fails closed.
resource_requirements: BASE-RES; bounded file-count/size/decompression limits; no GPU/net.
required_tests:
  - path-safety #10: symlink/junction/reserved-name/traversal/case/archive escapes blocked
  - Dec B: no deletion path exists without a valid approval
  - archive limits #11: entry-count/depth/decompression caps prevent archive bombs
  - write containment: writes outside the granted+canonical path scope are denied
  - atomicity: interrupted write leaves no partial/corrupt file
```

## Lifecycle

- **Initialization:** load path-authority policy + archive limits; wire to CMP-PERM/CMP-APPROVAL/CMP-AUDITW.
- **Runtime:** canonicalize → check grant (+ approval for delete) → perform bounded atomic op → audit
  destructive ops; reject any escape/limit breach as a security event.
- **Recovery:** atomic ops reconcile cleanly; no partial artifacts.

## Component-map change-control note

Adding CMP-FILEOP raises the authoritative component count to 40 (`00-COMPONENT-MAP.md` #40). This is recorded
as a change-control addition (PAL §7 / `00-DOCUMENTATION-INDEX.md`), correcting a prior omission — not a new
architectural decision (roadmap §PH-3 already names "safe file-op"). Cross-referenced in `RPH3-INTEGRATION.md`.
