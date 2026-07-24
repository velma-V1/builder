# Release Plan

**Status:** Authoritative planning record (L25.1) · **Phase:** PH-8
**Recorded:** July 24, 2026
**Governing:** `01O` (deployment/updates/release), `01I §2.23` (release identity), `01G` (verdicts), `01N` (activation independence). In force with `01R`.

## 1. Channels (`01O §2.40`)
`development`, `experimental`, `beta`, `release-candidate`, `stable` — independently selectable; Factory never moves an installation between channels silently.

## 2. Versioning & identity
Every release has a unique immutable version; semantic versioning when it accurately communicates compatibility (`01O §2.31-32`). Release tags identify the exact verified commit and artifact hashes (`01I §2.23`).

## 3. Release candidate build (gate G7)
Built from a clean identified Git commit with no unexplained local changes (`01O §2.33`). Release evidence records (`01O §3.9`): source commit + repo state; build-tool/compiler/packager/runtime versions; packaging OS build; dependency locks; SBOM; third-party license inventory; vulnerability-scan results; container image digests; immutable model identities; installer/executable/package/doc hashes; signing key/cert identifier; schema/migration versions; configuration profile; linked test-report identifiers; repeatable build instructions. An artifact that cannot be matched to its declared provenance cannot receive `PASS` (`01O §3.9`).

## 4. Lifecycle & failure-path verification (`01O §3.7`)
Interrupted install; interrupted update / power loss; failed migration; corrupted package; unknown/invalid/expired/revoked signature; artifact-hash mismatch; insufficient disk; missing network; missing/incompatible model; WSL/Docker unavailable; required reboot; snapshot creation/verification/restoration failure; upgrade from every supported prior version; unsupported-downgrade rejection; uninstall with retained data; full uninstall with selected removable data. A required failure-path test not completed is missing evidence and blocks the stable claim.

## 5. Windows 11 Home verification (`01O §2.36-37`, `01N`)
Release tests run on the declared supported Windows 11 Home baseline **without requiring activation**; activated and unactivated systems follow identical tests, functionality, support policy, production eligibility, and criteria. Representative hardware matching or weaker than the target PC (`01O §2.38`).

## 6. Severity gate & release verdict (`01O §2.41`, §6)
Every release candidate ends with one verdict: `PASS` / `FAIL` / `BLOCKED` / `INCONCLUSIVE`. **Stable** is allowed only when: verdict `PASS`; every required acceptance criterion and failure path has evidence; **zero unresolved critical or high-severity defects**; supported install/update/rollback/uninstall/recovery/offline paths pass; provenance and signing valid; documentation matches the verified release; no required approval outstanding. Documented low-severity defects may remain only when all governing requirements and criteria still pass (`01O §2.42`).

## 7. Support-claim honesty (`01O §2.39`)
Environments, rollback paths, channels, and capabilities not directly verified are labeled experimental/unverified/unsupported — never presented as verified.

## 8. Completion linkage
Stable release additionally requires the self-hosting transition complete (`01B` St.5/§6) and the VELMA validation build achievable (`PD §24`) per `docs/10 §16`. Consumed by `docs/release/INSTALLER-PLAN.md`, `UPDATE-AND-MIGRATION-PLAN.md`, `ROLLBACK-PLAN.md`, and the completion checklist.
