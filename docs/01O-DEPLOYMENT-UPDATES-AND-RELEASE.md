# Approved Deployment, Updates, and Release Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing deployment boundary

Factory's primary supported launch host is Windows 11 Home. Activated and unactivated installations receive identical support. Windows activation is entirely outside Factory and cannot affect installation, operation, testing, updating, packaging, verification, or release.

Factory remains local-first and offline-capable. Installation and updates must preserve operator control, persistent data, verified recovery, integrity, and reproducibility. Unsupported environments, rollback paths, or capabilities must never be represented as verified.

## 2. Approved Stage 12 decisions

1. **Initial host scope:** Native Linux host support is not required for the first release.
2. **Technical prerequisite checks:** Installation verifies Windows version, WSL2, Docker, virtualization capability, storage, RAM, GPU, drivers, and other approved technical requirements.
3. **No activation check:** Factory does not query or use Windows activation status as an installation, operation, testing, update, packaging, verification, or release gate.
4. **Controlled prerequisite installation:** Missing prerequisites may be installed only after explicit operator approval.
5. **No automatic BIOS modification:** Factory never modifies BIOS or firmware settings automatically.
6. **Actionable blocked setup:** Setup provides exact instructions when virtualization or another prerequisite is unavailable or disabled.
7. **Guided installer first:** Factory initially uses a guided installer that exposes storage, prerequisite, model, permission, and data-location choices.
8. **No polished one-click requirement for development:** A polished one-click installer is not required for development builds and is produced only after the core system stabilizes.
9. **Repeatable development setup:** Development builds provide a repeatable setup script or equivalent deterministic setup process.
10. **Minimal host modification:** Installation avoids altering unrelated system software, settings, services, paths, or policies.
11. **Separated storage domains:** Installation files, persistent Factory data, models, caches, logs, evidence, temporary state, and project workspaces use clearly separated directories.
12. **Selectable storage locations:** The operator may select approved storage locations when practical.
13. **Pre-install storage calculation:** Setup calculates required and recommended free space before installation or material updates.
14. **Models excluded from main installer:** AI models are not packaged inside the main Factory installer.
15. **Existing Ollama model detection:** Factory detects approved models already installed through Ollama and avoids unnecessary duplication.
16. **No automatic model download:** Missing models are presented to the operator and downloaded only with explicit approval.
17. **Model identity and integrity:** Downloaded models are verified for exact identity, version or tag, expected metadata, and available integrity evidence before use.
18. **Versioned state formats:** Configurations, databases, contracts, schemas, migrations, and persistent records use explicit versions.
19. **Transactional migrations:** State-changing updates use transactional or equivalently fail-safe migrations.
20. **Pre-update recovery snapshot:** Every update that changes runtime or persistent state creates and verifies an applicable Factory recovery snapshot before activation.
21. **Documentation-only exception:** Documentation-only updates do not require a runtime-state recovery snapshot.
22. **No unattended update installation:** Factory never installs updates automatically without operator approval.
23. **Operator-enabled update checks:** Factory checks for updates automatically only when the operator enables approved network checks.
24. **Signed and verified packages:** Update and release packages use signatures and integrity verification appropriate to the distribution method.
25. **Complete update review:** Before approval, the update view shows version, changes, risks, migrations, affected components, hardware and storage impact, known limitations, verification status, and rollback plan.
26. **Staged update activation:** Updates are staged and verified before replacing or activating the working installation.
27. **No permanent duplicate installation requirement:** Factory does not retain two complete permanent installations solely for rollback; it uses verified recovery state and retained versioned installation packages.
28. **Tested rollback paths only:** Automatic downgrade between every version is not required. Only explicitly supported and tested rollback paths are allowed.
29. **Fail-closed incompatible downgrade:** Incompatible schema or state downgrades fail closed rather than risking corruption.
30. **Security fixes retain gates:** Critical security updates may receive priority but cannot bypass applicable testing, integrity, recovery, or approval gates.
31. **Immutable release identity:** Every release has a unique immutable version.
32. **Semantic versioning:** Factory uses semantic versioning when it accurately communicates compatibility and change scope.
33. **Clean source baseline:** Release candidates are built from a clean, identified Git commit with no unexplained local changes.
34. **Complete release identity:** Release packages identify the source commit, dependency locks, schema and migration versions, model requirements, toolchain versions, configuration profile, and artifact hashes.
35. **Lifecycle release verification:** Release verification covers installation, launch, core task execution, sandboxing, permissions, recovery, updating, rollback where supported, and uninstalling.
36. **Windows 11 Home verification:** Release tests run on Windows 11 Home without requiring activation.
37. **Identical activation-state behavior:** Activated and unactivated Windows 11 Home systems follow the same Factory tests, functionality, support policy, and release criteria.
38. **Representative hardware testing:** Release testing uses hardware matching or weaker than the target PC when practical.
39. **No untested support claims:** Environments not directly verified are labeled experimental, unverified, or unsupported.
40. **Release-channel separation:** Development, experimental, beta, release-candidate, and stable builds are clearly distinguished.
41. **Stable severity gate:** Stable release requires zero unresolved critical or high-severity defects.
42. **Bounded low-severity limitations:** Documented low-severity defects may remain only when all governing requirements and release acceptance criteria still pass.
43. **Known-limitations disclosure:** Every known release limitation is documented accurately.
44. **Configuration-derived documentation:** Installation and release documentation is generated from or checked against the verified release configuration to prevent drift.
45. **Complete uninstall:** Factory supports a verified complete application uninstall path.
46. **Persistent-data protection:** Uninstall does not automatically delete projects, models, evidence, settings, databases, recovery exports, or other persistent data.
47. **Separate data-removal choice:** Uninstall may offer a clearly separated, consequence-labeled optional data-removal operation.
48. **Portable recovery exports:** Recovery exports remain readable and usable without an active Factory installation through documented standard formats and tools where practical.
49. **Verified operational guides:** Stable release requires verified installation, update, supported rollback, uninstall, and recovery instructions.
50. **Activation exclusion:** No installation, update, verification, packaging, or release gate may depend on Windows activation.

## 3. Operating boundaries

- Activated and unactivated Windows 11 Home receive identical Factory support.
- Installation checks technical compatibility, never licensing or activation status.
- Guided setup and repeatable scripts precede a polished one-click installer.
- Models and persistent data remain separately managed from the replaceable application installation.
- Updates are signed or equivalently authenticated, staged, verified, recoverable, and operator-approved.
- Factory never labels an untested platform, rollback path, installation mode, or capability as supported.

## 4. Release verdict

Every release candidate ends with one explicit verdict:

```text
PASS
FAIL
BLOCKED
INCONCLUSIVE
```

A release may be labeled stable only when the verdict is `PASS`, every required acceptance criterion has evidence, all critical and high-severity defects are resolved, the supported installation and lifecycle paths pass, and no required approval remains outstanding.

## 5. Acceptance criteria

This decision is satisfied only when tests prove that:

1. Factory installs, launches, operates, updates, recovers, packages, and completes release verification on Windows 11 Home without an activation dependency;
2. activated and unactivated Windows 11 Home follow identical Factory behavior and support rules;
3. prerequisite checks identify genuine technical requirements without using activation status;
4. state-changing updates create verified recovery protection and cannot leave a partially migrated authoritative state;
5. update and release packages have verifiable identity and integrity;
6. release packages are reproducibly tied to an exact clean source commit and declared toolchain, schema, dependency, model, and configuration requirements;
7. uninstall preserves persistent data unless the operator separately approves deletion;
8. recovery exports remain interpretable without relying on the currently installed Factory version;
9. unsupported or untested environments and rollback paths are not presented as verified;
10. installation, update, rollback where supported, recovery, and uninstall documentation matches the verified release.