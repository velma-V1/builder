# Update & Migration Plan

**Status:** Authoritative planning record (L25.1) · **Phase:** PH-8 (schema/migration foundation PH-1/PH-7)
**Recorded:** July 24, 2026
**Governing:** `01O §2.18-30/§3.5-3.6`, `01M` (snapshots), `01 §15`/`02 §6` (schema/migration versioning), `01H §2.30` (control-plane protection). In force with `01R`.

## 1. Versioned state & transactional migrations
Configurations, databases, contracts, schemas, migrations, and persistent records use explicit versions (`01O §2.18`). State-changing updates use transactional or equivalently fail-safe migrations (`01O §2.19`); the runner verifies the migration SHA-256 before applying, executes in one transaction, and records the version only after success (Section 1 plan Task 4). Incompatible schema/state downgrades **fail closed** (`01O §2.29`).

## 2. Pre-update recovery snapshot (`01O §2.20`)
Every update that changes runtime or persistent state creates and verifies an applicable Factory recovery snapshot **before activation**; failure to create or verify the snapshot **blocks** the update. Documentation-only updates do not require a Factory-state snapshot but remain signed, integrity-verified, staged, and safely replaceable (`01O §2.21`).

## 3. Signing & trust management (`01O §3.5`)
Approved release public key embedded/provisioned at install; documented key-rotation and compromised-key-revocation procedures; reject unknown/expired/revoked/malformed/invalid signatures; **separate** verification of package signatures and declared artifact hashes; auditable signing-cert/key identifier; **no unsigned emergency-update exception**. Trust-store changes are protected state changes requiring explicit authorization, evidence, rollback protection, and verification.

## 4. Staged activation & operator control (`01O §2.22-26`)
No unattended update installation — updates require operator approval. Update checks run only when the operator enables approved network checks and transmit only minimum required version + channel. Before approval the update view shows version, channel, changes, risks, migrations, affected components, hardware/storage impact, known limitations, verification status, provenance, and rollback plan. Updates are staged and verified before replacing/activating the working installation.

## 5. Executable rollback window (`01O §2.27`, §3.6)
Factory does not keep two permanent installations. During staging the previous executable version remains intact and locally recoverable until all required migrations, startup checks, service-health checks, compatibility checks, and operational verification pass. Update commitment atomically selects the new version; the previous executable is removed only after commitment + expiration of any approved rollback hold. Factory-state snapshots do not replace executable rollback protection.

## 6. Security fixes (`01O §2.30`)
Critical security updates may receive priority but cannot bypass applicable signing, testing, integrity, recovery, or approval gates.

## 7. Control-plane protection
Updates that would change governing controls or their enforcers use the separate architecture-change process, never ordinary Improvement Packets (`01H §2.30`). Consumed by `docs/release/ROLLBACK-PLAN.md` and the release plan.
