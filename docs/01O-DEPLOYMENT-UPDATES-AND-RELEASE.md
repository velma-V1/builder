# Approved Deployment, Updates, and Release Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026  
**Clarified:** July 23, 2026

## 1. Governing deployment boundary

Factory's primary supported launch host is 64-bit Windows 11 Home. Activated and unactivated installations receive identical support. Windows activation is entirely outside Factory and cannot affect installation, operation, testing, updating, packaging, verification, supported-production eligibility, or release.

Factory remains local-first and offline-capable. Installation and updates must preserve operator control, persistent data, verified recovery, integrity, provenance, reproducibility, and explicit support boundaries. Unsupported environments, rollback paths, channels, or capabilities must never be represented as verified.

## 2. Approved Stage 12 decisions

1. **Initial host scope:** Native Linux host support is not required for the first release.
2. **Technical prerequisite checks:** Installation verifies the versioned supported Windows baseline, WSL2, Docker, CPU virtualization capability, storage, RAM, GPU, VRAM, drivers, and other approved technical requirements.
3. **No activation dependency:** Factory does not query or use Windows activation status as an installation, operation, testing, update, packaging, verification, supported-production, or release gate.
4. **Controlled prerequisite installation:** Missing prerequisites may be installed only after explicit operator approval.
5. **No automatic BIOS modification:** Factory never modifies BIOS or firmware settings automatically.
6. **Actionable blocked setup:** Setup provides exact instructions when virtualization or another prerequisite is unavailable or disabled.
7. **Guided installer first:** Factory initially uses a guided installer that exposes storage, prerequisite, model, permission, channel, and data-location choices.
8. **No polished one-click requirement for development:** A polished one-click installer is not required for development builds and is produced only after the core system stabilizes.
9. **Repeatable development setup:** Development builds provide a repeatable setup script or equivalent deterministic setup process.
10. **Minimal host modification:** Installation avoids altering unrelated system software, settings, services, paths, or policies.
11. **Separated storage domains:** Installation files, persistent Factory data, models, caches, logs, evidence, temporary state, and project workspaces use clearly separated directories.
12. **Selectable storage locations:** The operator may select approved storage locations when practical.
13. **Pre-install storage calculation:** Setup calculates required and recommended free space before installation or material updates.
14. **Models excluded from main installer:** AI models are not packaged inside the main Factory installer.
15. **Existing Ollama model detection:** Factory detects approved models already installed through Ollama and avoids unnecessary duplication.
16. **No automatic model download:** Missing models are presented to the operator and downloaded only with explicit approval.
17. **Model identity and integrity:** Downloaded or detected models are verified using an immutable digest, verified manifest, or equivalent deterministic identity rather than model name or mutable tag alone.
18. **Versioned state formats:** Configurations, databases, contracts, schemas, migrations, and persistent records use explicit versions.
19. **Transactional migrations:** State-changing updates use transactional or equivalently fail-safe migrations.
20. **Pre-update recovery snapshot:** Every update that changes runtime or persistent state creates and verifies an applicable Factory recovery snapshot before activation. Failure to create or verify the required snapshot blocks the update.
21. **Documentation-only exception:** Documentation-only updates do not require a Factory-state recovery snapshot, but the documentation package must still be authenticated, integrity-verified, staged, and safely replaceable.
22. **No unattended update installation:** Factory never installs updates automatically without operator approval.
23. **Operator-enabled update checks:** Factory checks for updates only when the operator enables approved network checks. A check transmits only the minimum required version and selected-channel information.
24. **Signed and verified packages:** Update, documentation, installer, and release packages require an approved signature plus independent artifact-hash verification. No unsigned emergency-update exception is allowed.
25. **Complete update review:** Before approval, the update view shows version, channel, changes, risks, migrations, affected components, hardware and storage impact, known limitations, verification status, provenance, and rollback plan.
26. **Staged update activation:** Updates are staged and verified before replacing or activating the working installation.
27. **No permanent duplicate installation requirement:** Factory does not retain two complete permanent installations solely for rollback. During an update, the previous executable application version remains temporarily available until migration, startup, health checks, and operational verification succeed; it is removed only after update commitment.
28. **Tested rollback paths only:** Automatic downgrade between every version is not required. Only explicitly supported and tested rollback paths are allowed.
29. **Fail-closed incompatible downgrade:** Incompatible schema or state downgrades fail closed rather than risking corruption.
30. **Security fixes retain gates:** Critical security updates may receive priority but cannot bypass applicable signing, testing, integrity, recovery, or approval gates.
31. **Immutable release identity:** Every release has a unique immutable version.
32. **Semantic versioning:** Factory uses semantic versioning when it accurately communicates compatibility and change scope.
33. **Clean source baseline:** Release candidates are built from a clean, identified Git commit with no unexplained local changes.
34. **Complete release identity:** Release packages identify the source commit, dependency locks, schema and migration versions, immutable model and container identities, toolchain versions, packaging operating-system build, configuration profile, software bill of materials, third-party license inventory, vulnerability-scan results, artifact hashes, signing-key identifier, test-report identifiers, and repeatable build instructions.
35. **Lifecycle release verification:** Release verification covers installation, launch, core task execution, sandboxing, permissions, recovery, updating, supported rollback, failure paths, channel behavior, and uninstalling.
36. **Windows 11 Home verification:** Release tests run on the declared supported Windows 11 Home baseline without requiring activation.
37. **Identical activation-state behavior:** Activated and unactivated Windows 11 Home systems follow the same Factory tests, functionality, support policy, production eligibility, and release criteria.
38. **Representative hardware testing:** Release testing uses hardware matching or weaker than the target PC when practical.
39. **No untested support claims:** Environments not directly verified are labeled experimental, unverified, or unsupported.
40. **Release-channel separation:** Development, experimental, beta, release-candidate, and stable channels remain independently selectable. Factory never silently moves an installation between channels.
41. **Stable severity gate:** Stable release requires zero unresolved critical or high-severity defects.
42. **Bounded low-severity limitations:** Documented low-severity defects may remain only when all governing requirements and release acceptance criteria still pass.
43. **Known-limitations disclosure:** Every known release limitation is documented accurately.
44. **Configuration-derived documentation:** Installation and release documentation is generated from or checked against the verified release configuration to prevent drift.
45. **Complete Factory application removal:** Uninstall supports verified removal of Factory-owned application binaries, registrations, services, scheduled tasks, auto-launch entries, shortcuts, and temporary files.
46. **Persistent-data protection:** Uninstall does not automatically delete Factory databases, evidence, configuration, models, Docker volumes or images, WSL distributions, recovery snapshots, project workspaces, Git repositories, recovery exports, or other persistent data.
47. **Separate data-removal choice:** Uninstall may offer a clearly separated, consequence-labeled optional removal operation for operator-selected Factory-owned persistent data. Shared components such as Docker, WSL, Ollama, or GPU drivers are never removed automatically.
48. **Portable recovery exports:** Recovery exports remain readable and usable without an active Factory installation through documented standard formats and tools where practical.
49. **Verified operational guides:** Stable release requires verified installation, update, supported rollback, uninstall, recovery, channel-selection, and offline-operation instructions.
50. **Activation exclusion:** No installation, update, verification, packaging, supported-production, or release gate may depend on Windows activation.

## 3. Nine binding deployment and release clarifications

### 3.1 Activation independence

Development, testing, installation, Factory core operation, supported-production eligibility, packaging, verification, and release remain fully functional on unactivated Windows 11 Home. Factory must not query activation status as an eligibility check or hard-code activation into any runtime, installer, test, or release path.

Windows licensing or activation may be handled separately by the operator or operating-system vendor, but it is not Factory evidence and cannot affect a Factory verdict.

### 3.2 Versioned supported Windows baseline

Every release records one versioned support profile containing at least:

- 64-bit Windows 11 Home;
- minimum supported Windows build;
- minimum WSL version and Linux kernel;
- supported Docker Engine or Docker Desktop versions;
- minimum and recommended RAM and storage;
- minimum supported CPU virtualization features;
- minimum GPU and VRAM when GPU operation is required;
- minimum supported GPU-driver and runtime versions;
- required reboots, Windows features, and host capabilities.

The installer, release metadata, tests, and documentation consume this support profile rather than duplicating values as scattered constants.

### 3.3 Required, recommended, and informational checks

Every prerequisite or compatibility check is classified as exactly one of:

```text
REQUIRED
RECOMMENDED
INFORMATIONAL
```

- `REQUIRED` failure blocks installation or the affected capability.
- `RECOMMENDED` failure produces a visible warning and requires an explicit operator override when proceeding is safe.
- `INFORMATIONAL` results are recorded but do not block installation.

A recommendation or informational warning must never be treated as a required failure without an approved support-profile change.

### 3.4 External runtime-artifact governance

Docker images, WSL packages, Ollama installers, Python and runtime packages, GPU runtime components, and other externally obtained runtime artifacts follow the same controlled acquisition principles as models:

- explicit approval before download;
- approved source and retrieval record;
- exact version, immutable digest, or verified manifest;
- integrity verification before use;
- license and compatibility metadata when available;
- offline import capability where practical.

Mutable Docker tags, package names, or model names alone are not sufficient release identities. Container images must record immutable image digests.

### 3.5 Update-signing trust management

Factory's update trust system requires:

- an approved release public key embedded or securely provisioned during installation;
- a documented signing-key rotation procedure;
- a documented compromised-key revocation procedure;
- rejection of unknown, expired, revoked, malformed, or invalid signatures;
- separate verification of package signatures and declared artifact hashes;
- an auditable signing-certificate or key identifier;
- no unsigned emergency-update exception.

Trust-store changes are protected state changes and require explicit authorization, evidence, rollback protection, and verification.

### 3.6 Temporary executable rollback during updates

Factory does not maintain two permanent installations. During update staging, the previous executable application version remains intact and locally recoverable until all required migrations, startup checks, service health checks, compatibility checks, and operational verification pass.

Update commitment atomically selects the new version. The previous executable version may be removed only after successful commitment and expiration of any approved rollback hold. Factory-state snapshots do not replace executable rollback protection.

### 3.7 Lifecycle and failure-path verification

Applicable release verification includes at least:

- interrupted installation;
- interrupted update or simulated power loss;
- failed schema migration;
- corrupted package;
- unknown, invalid, expired, or revoked signature;
- artifact-hash mismatch;
- insufficient disk space;
- missing network access;
- missing or incompatible model;
- WSL or Docker unavailable;
- required reboot handling;
- recovery-snapshot creation failure;
- recovery-snapshot verification failure;
- recovery-restoration failure;
- upgrade from every supported prior version;
- unsupported downgrade rejection;
- uninstall with persistent data retained;
- full uninstall with explicitly selected removable data.

A required failure-path test that is not completed must be reported as missing evidence and blocks the applicable stable-release claim.

### 3.8 Uninstall ownership boundaries

Complete Factory application removal means removing Factory-owned executable and operating integration material, including binaries, registrations, services, scheduled tasks, auto-launch entries, shortcuts, and temporary application files.

The following remain unless separately and explicitly selected for removal:

- Factory databases and evidence;
- configuration;
- models;
- Docker volumes and images;
- Factory-specific WSL distributions;
- recovery snapshots and exports;
- project workspaces;
- Git repositories.

Shared host components such as Docker, WSL, Ollama, Python installations, GPU runtimes, or GPU drivers are not removed automatically. GitHub project repositories remain user-controlled data and remain outside Factory recovery snapshots.

### 3.9 Release provenance and dependency evidence

Every release evidence package records at least:

- exact source commit and repository state;
- build-tool, compiler, linker, packager, and runtime versions;
- operating-system build used for packaging;
- dependency locks;
- software bill of materials;
- third-party license inventory;
- dependency vulnerability-scan results and exceptions;
- container image digests;
- immutable model identities or verified manifests;
- installer, executable, package, and documentation hashes;
- signing certificate or key identifier;
- schema and migration versions;
- configuration profile;
- linked test-report and evidence-package identifiers;
- reproducible or repeatable build instructions.

A release artifact that cannot be matched to its declared provenance cannot receive a `PASS` verdict.

## 4. Additional implementation boundaries

- Documentation-only updates do not require a Factory-state snapshot, but they remain signed, integrity-verified, staged, and safely replaceable.
- Stable, beta, experimental, release-candidate, and development channels remain independently selectable and never change silently.
- Update checks transmit only minimum required version and channel information after operator enablement.
- Failure to create or verify a required recovery snapshot blocks update activation.
- GitHub project repositories remain outside Factory recovery snapshots and are clearly identified as user-controlled persistent data.
- Offline-capable Factory operation does not claim that every prerequisite can be installed offline. Documentation distinguishes offline runtime operation from offline initial installation.
- Model, container, and runtime-component identity uses immutable digests or verified manifests wherever supported.

## 5. Operating boundaries

- Activated and unactivated Windows 11 Home receive identical Factory support.
- Installation checks technical compatibility, never licensing or activation status.
- Required, recommended, and informational compatibility results remain distinct.
- Guided setup and repeatable scripts precede a polished one-click installer.
- Models, runtime artifacts, and persistent data remain separately governed from the replaceable application installation.
- Updates are signed, hash-verified, staged, transactionally migrated, executable-recoverable, Factory-state-recoverable, and operator-approved.
- Factory never labels an untested platform, rollback path, channel, installation mode, or capability as supported.

## 6. Release verdict

Every release candidate ends with one explicit verdict:

```text
PASS
FAIL
BLOCKED
INCONCLUSIVE
```

A release may be labeled stable only when the verdict is `PASS`, every required acceptance criterion and failure path has evidence, all critical and high-severity defects are resolved, the supported installation and lifecycle paths pass, provenance and signing evidence are valid, and no required approval remains outstanding.

## 7. Acceptance criteria

This decision is satisfied only when tests prove that:

1. Factory installs, launches, operates, updates, recovers, packages, and completes release verification on the declared Windows 11 Home baseline without an activation dependency;
2. activated and unactivated Windows 11 Home follow identical Factory behavior and support rules;
3. a single versioned support profile controls installer checks, release metadata, tests, and documentation;
4. required, recommended, and informational checks produce the correct blocking or nonblocking behavior;
5. models, container images, WSL packages, runtimes, and other external artifacts require approved sources, immutable identities, and integrity verification;
6. state-changing updates cannot begin without verified recovery protection and cannot leave partially migrated authoritative state;
7. the previous executable version remains recoverable until update commitment succeeds;
8. unknown, invalid, expired, revoked, or incorrectly signed packages are rejected, and artifact hashes are checked independently;
9. required lifecycle and failure-path tests pass, including supported-version upgrades and unsupported downgrade rejection;
10. release packages are tied to an exact clean source commit, complete provenance, SBOM, license inventory, vulnerability results, immutable dependency identities, signing identity, and linked test evidence;
11. channel selection remains explicit and installations never move silently between channels;
12. uninstall removes Factory-owned application material while preserving persistent and shared components unless the operator separately approves eligible data removal;
13. GitHub project repositories remain outside Factory recovery snapshots and are treated as user-controlled persistent data;
14. recovery exports remain interpretable without relying on the currently installed Factory version;
15. release documentation accurately distinguishes offline runtime operation from offline initial installation;
16. unsupported or untested environments, rollback paths, channels, and capabilities are not presented as verified;
17. installation, update, rollback where supported, recovery, channel-selection, offline-operation, and uninstall documentation matches the verified release.