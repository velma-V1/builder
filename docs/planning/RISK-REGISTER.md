# Factory Risk Register

**Status:** Authoritative planning record (L25.1)
**Recorded:** July 24, 2026
**Sources:** every supplement's failure modes, `01M`, `01H`, Pass-1/Pass-7 findings. In force with `01R`. A residual-risk acceptance requires the `01G §3.4` bounded-exception record.

Fields: ID · Category · Description · Affected components · Likelihood · Impact · Detection · Preventive controls · Mitigation · Contingency · Owner · Blocking threshold · Evidence requirement.

## Architecture
- **RISK-ARCH-01** · R1–R5 amendments unrecorded before dependent implementation → drift. Affected: Orchestrator/Watchdog/WSSM, contract system. L Med / I High. Detect: index/spec review at phase entry. Prevent: `01R` recorded (done). Mitigate: apply before PH-2/3/6. Contingency: block affected phase. Owner: architect/PH-2. Threshold: blocks PH-2/3/6 entry. Evidence: `01R` + supersession pointers (satisfied 2026-07-24).
- **RISK-ARCH-02** · Orchestrator/Watchdog split misimplemented (writer authority leaks). Affected: Orchestrator, Watchdog. L Med / I High. Detect: no-direct-write + separate-process tests. Prevent: `01M §1` separation. Mitigate: refactor boundary. Contingency: fail closed, block PH-3. Owner: PH-3. Threshold: blocks PH-3 promotion. Evidence: sole-writer + read-only tests PASS.

## Security
- **RISK-SEC-01** · TOCTOU gap between policy decision and file op. Affected: permission, file-op. L Med / I High. Detect: path-safety (#10). Prevent: `revalidate_before_use` (S1 §14). Mitigate: reject on ancestor change. Contingency: block op. Owner: PH-1/3. Threshold: blocks PH-1/3. Evidence: TOCTOU test PASS.
- **RISK-SEC-02** · malicious repo / prompt-injection treated as governing. Affected: tool gateway, sandbox, memory, research. L Med / I High. Detect: trust-boundary (#6). Prevent: `01K §2.28`, untrusted-by-default. Mitigate: notify operator (`PD §19`). Contingency: quarantine input. Owner: PH-3/5. Threshold: blocks any untrusted-input promotion. Evidence: instruction-distrust + injection tests PASS.

## Isolation
- **RISK-ISO-01** · sandbox escape / writable host mount / privilege escalation. Affected: sandbox mgr. L Low-Med / I Critical. Detect: sandbox-escape (#7), privilege (#8). Prevent: `01E §3.1-3.2`, non-root, no host socket/namespaces. Mitigate: destroy env, security clearance (`04 §7`). Contingency: stop lane. Owner: PH-5. Threshold: any hit halts Factory. Evidence: `01E` 32 criteria PASS.
- **RISK-ISO-02** · (resolved) Windows-native execution scope. **Closed by Decision C** — excluded from v1; WSL2+Docker only. Residual: enforcement test that no non-WSL2/Docker exec path exists. Owner: PH-5. Threshold: blocks PH-5 freeze. Evidence: category-7/26 exclusion test PASS.

## Data-loss
- **RISK-DATA-01** · deletion destroys pre-existing/shared files. Affected: permission. **L Low (Decision B conservative)** / I High. Detect: deletion-policy (#9). Prevent: `01 §11` approval-gated (Dec B). Mitigate: approval + recreation/rollback proof. Contingency: restore from checkpoint. Owner: PH-3. Threshold: blocks PH-3 if any auto-delete of non-disposable. Evidence: deletion-policy test PASS (approval-gated).
- **RISK-DATA-02** · secret leakage into logs/evidence/Promotion Package/memory. Affected: secret broker, evidence, Promotion, memory. L Med / I High. Detect: secret-handling (#11), pre-finalize scan. Prevent: `01E §3.4` redaction/exclusion. Mitigate: block export until removed. Contingency: quarantine artifact. Owner: PH-5. Threshold: blocks staging export/promotion. Evidence: no-embed + redaction PASS.

## Recovery
- **RISK-REC-01** · snapshot corruption / failed candidate replaces active. Affected: snapshot mgr. L Low / I Critical. Detect: snapshot-integrity (#19), isolated-restore (#20). Prevent: `01M §3.9` candidate-tested; active unchanged until pass. Mitigate: keep last verified; quarantine candidate. Contingency: block activation on missing/stale snapshot. Owner: PH-7. Threshold: blocks PH-7 + any update (`01O §2.20`). Evidence: candidate-restore PASS.
- **RISK-REC-02** · non-idempotent recovery duplicates changes on replay. Affected: journal, Orchestrator. L Med / I High. Detect: journal-replay (#17), crash (#16). Prevent: `01M §2.18` idempotent ops. Mitigate: replay-safe transitions. Contingency: fail closed to BLOCKED. Owner: PH-2. Threshold: blocks PH-2. Evidence: replay-idempotency PASS.

## Resource
- **RISK-RES-01** · 12 GB VRAM overcommit / GPU thrash / thermal (RTX 4070 Super). Affected: Resource Scheduler, Watchdog. L Med / I Med-High. Detect: resource-pressure (#27), scheduler (#28). Prevent: `01J §3.3`, ≤1 GPU-heavy, reservations, anti-thrash. Mitigate: reduce parallelism (`01D §2.24`). Contingency: checkpointed pause. Owner: PH-4. Threshold: blocks PH-4. Evidence: overcommit-prevention + anti-thrash PASS.

## Model
- **RISK-MODEL-01** · roster model unavailable/deprecated → silent substitution. Affected: router. L Med / I High. Detect: model-routing (#29), fallback (#30). Prevent: `03 §6/§8`, `01J §2.14` no-silent-sub. Mitigate: paired/local fallback. Contingency: pause task; approval for replacement. Owner: PH-4. Threshold: blocks PH-4; pauses task at runtime. Evidence: no-silent-substitution PASS.
- **RISK-MODEL-02** · model self-certification accepted as evidence. Affected: router, verification engine. L Med / I High. Detect: evidence-integrity (#31). Prevent: `01G §1`, `01J §1`. Mitigate: reject model-only claims. Contingency: block promotion. Owner: PH-7. Threshold: blocks promotion. Evidence: no-model-only-pass PASS.

## Dependency
- **RISK-DEP-01** · pinned tool versions (mypy 2.3.0, pytest 9.1.1, Ruff 0.15.22, rfc8785 0.1.4, hatchling 1.27.0) unavailable/incompatible. Affected: contract system, all Python. L Med / I Med. Detect: `uv lock`/`uv sync --frozen` at PH-1. Prevent: pinned lockfile, offline import (`01O §3.4`). Mitigate: nearest approved compatible pin, recorded. Contingency: block PH-1 env. Owner: PH-1. Threshold: blocks PH-1 setup. Evidence: resolved `uv.lock` + green static checks.
- **RISK-DEP-02** · Codex/VS Code/OpenHands/hosted creeps in as required dependency. Affected: all. L Low-Med / I High. Detect: dependency review, `06 §10`. Prevent: `01A §3/§9/§10`, IDE-independence tests. Mitigate: remove; adapter disabled. Contingency: block phase promotion. Owner: each phase. Threshold: blocks any phase whose removal breaks it. Evidence: runs with those absent (`01A §13`).

## Windows / WSL
- **RISK-WIN-01** · WSL2/virtualization disabled/unavailable on target Windows 11 Home. Affected: installer, sandbox. L Med / I High. Detect: installer (#23), prerequisite checks. Prevent: `01O §3.2-3.3` REQUIRED check + actionable instructions. Mitigate: guide operator to enable. Contingency: block install (REQUIRED). Owner: PH-8. Threshold: blocks install/PH-5 exec. Evidence: prerequisite-check + actionable-blocked-setup PASS.

## Docker
- **RISK-DOCKER-01** · Docker socket exposure / privileged / nested control. Affected: sandbox mgr. L Low / I Critical. Detect: privilege (#8), sandbox-escape (#7). Prevent: `01E §3.1` prohibited privileges, no host socket. Mitigate: deny by default; quarantine. Contingency: halt exec. Owner: PH-5. Threshold: blocks PH-5. Evidence: host-control-denial PASS.

## Installer
- **RISK-INSTALL-01** · installer requires activation or modifies unrelated host state. Affected: installer. L Low / I Med-High. Detect: installer (#23), Windows-Home (#26). Prevent: `01N`, `01O §2.10/§3.1` no activation gate, minimal host mod. Mitigate: fix installer; label unsupported honestly. Contingency: block stable release. Owner: PH-8. Threshold: blocks stable. Evidence: unactivated-install PASS + no-activation-gate.

## Update
- **RISK-UPDATE-01** · unsigned/tampered update, or update without recovery snapshot. Affected: updater. L Low / I Critical. Detect: updater/rollback (#21), signing. Prevent: `01O §3.5` signed+hash-verified, snapshot-gate, no unsigned exception. Mitigate: reject; retain previous executable. Contingency: roll back. Owner: PH-8. Threshold: blocks update activation. Evidence: signature-rejection + snapshot-gate PASS.

## Verification
- **RISK-VERIF-01** · verification weakened to force a pass (anti-gaming). Affected: ETM, verification engine, evidence store. L Med / I High. Detect: anti-weakening controls. Prevent: `01G §3.2`, protected component (`01H §4.1`). Mitigate: reject change; log security event. Contingency: block + audit. Owner: PH-7. Threshold: blocks affected criterion + promotion. Evidence: anti-weakening/anti-gaming PASS.
- **RISK-VERIF-02** · flaky tests provide required promotion evidence. Affected: verification engine. L Med / I Med-High. Detect: flaky numeric policy (`01G §3.5`). Prevent: ≤2 retries, `UNSTABLE`, quarantine thresholds. Mitigate: quarantine; block required evidence. Contingency: reinstate via 5 clean passes. Owner: PH-7. Threshold: blocks required-criterion PASS. Evidence: flaky-policy + quarantine PASS.

## Schedule / complexity
- **RISK-SCHED-01** · scope blowup (8 sections + 15 supplements) / over-ambitious parallelism / state-vocabulary complexity. Affected: all. L High / I Med-High. Detect: roadmap gate reviews, dependency/workstream maps. Prevent: `05` drift rules, ≤3 workstreams, independence proof before parallel. Mitigate: serialize when unproven; defer non-v1 (research/self-improvement). Contingency: single-workstream fallback. Owner: architect/roadmap. Threshold: blocks parallel activation without independence proof. Evidence: Workstream Map independence proofs + phase gate PASS.
