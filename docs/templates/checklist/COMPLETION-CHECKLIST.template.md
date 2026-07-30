# Completion Checklist — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** L26 produced record
**Governing:** `01 §13` (task completion gate), `01G §27/§30` (evidence-complete promotion), `01O §6` (release verdict).
**Rule:** a checklist edit that weakens a completion condition is a `01G §3.2` event.

## Task/phase completion (`01 §13`)
- [ ] all required deliverables exist
- [ ] owned-path and forbidden-path checks pass
- [ ] required tests pass in the approved environment
- [ ] applicable failure-path / security / regression / visual / installation / launch evidence present
- [ ] Worker+Reviewer (or workstream) records present
- [ ] **every required acceptance criterion has a complete ETM chain with verdict `PASS`** (`01G §3.1`)
- [ ] unresolved findings cleared or accurately classified as permitted limitations
- [ ] exact changed-file list, commands, test results, checkpoint, and rollback path recorded
- [ ] `risk_class` set; `autonomy_level` recorded (Dec A)
- [ ] deletion (if any) was approval-gated (Dec B)
- [ ] no required approval outstanding
- [ ] package-level verdict = `PASS`

## Phase-exit gate (adds)
- [ ] every governing-supplement acceptance criterion PASS
- [ ] phase integration gate passed; evidence package finalized + integrity-protected
- [ ] no unresolved critical/high defect
- [ ] operator phase-exit approval; applicable self-hosting cutover (St.1–5) approved

## Stable-release gate (`01O §6`, adds)
- [ ] release verdict `PASS`; every required criterion + failure path has evidence
- [ ] zero unresolved critical/high-severity defects
- [ ] supported install/update/rollback/uninstall/recovery/offline paths pass on unactivated Windows 11 Home
- [ ] provenance + signing valid; documentation matches verified release
- [ ] self-hosting transition complete (`01B` St.5/§6); VELMA validation build achievable (`PD §24`)

**Completion is a deterministic evidence state, not the existence of generated sections.**
