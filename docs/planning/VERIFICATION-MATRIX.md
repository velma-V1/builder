# Requirement-to-Verification Matrix

**Status:** Derived/non-overriding reference (L25.D)
**Recorded:** July 24, 2026
**Sources:** all supplements' acceptance criteria, `PD` success criteria, `01G` (ETM + verdicts, R5), `docs/planning/TEST-STRATEGY.md`. In force with `01R`.

Regenerated as criteria/tests change; any criterion edit after implementation-start obeys the `01G §3.2` anti-weakening control. Every required criterion maps through the `01G §3.1` ETM chain to a promotion-eligible verdict (`PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT_TESTABLE`).

## Environments
`ENV-DEV` local dev (uv/pytest, Windows 11 Home dev path) · `ENV-SANDBOX` disposable non-root WSL2+Docker · `ENV-CLEAN` clean recreated env · `ENV-CLEAN-WIN` clean-machine unactivated Windows 11 Home · `ENV-ISO-RESTORE` isolated snapshot-restoration env · `ENV-OFFLINE` network-disabled.

## Test-category coverage map (35 categories)

| # | Category | Component(s) | Task (phase) | Requirement | Environment | Evidence | Promotion gate |
|---|---|---|---|---|---|---|---|
|1|unit|all (esp. contract system)|per-task, every phase|`01G §4`|ENV-DEV|per-task ETM + ≥95% cov|task promotion|
|2|integration|integration coordinator + pair|phase integration tasks|`01D §2.16`|ENV-DEV/SANDBOX|integration pkg|IP-2..5|
|3|system|whole Factory|PH-7/PH-8|`01G §4`; `PD §24`|ENV-CLEAN-WIN|system evidence|PH-8/stable|
|4|regression|changed+affected|every phase|`01G §2.4`; `04 §4`|ENV-DEV|ETM rows|task+phase|
|5|security|PH-3 spine, sandbox|security tasks|`01K`; `01G §2.8`; S1 §14|ENV-SANDBOX|security evidence|VM-2|
|6|trust-boundary|boundary components|PH-3/4/5/7|`01K §1`; `01Q §1`|ENV-SANDBOX|trust-boundary evidence|phase|
|7|sandbox-escape|sandbox mgr|PH-5|`01E §3.1/§3.6`|ENV-SANDBOX|escape-denial|PH-5|
|8|privilege|sandbox mgr, permission|PH-3/5|`01E §3.2`; `01K §2.13-14`|ENV-SANDBOX|privilege-denial|PH-3/5|
|9|permission|permission, approval|PH-3|`01K §2.4-8`; S1 §4.5|ENV-DEV/SANDBOX|permission evidence|PH-3|
|10|path-safety|path authority, file-op|PH-1/3/5|`01K §2.26-27`; S1 §14|ENV-DEV(+Win)|path-attack evidence|PH-1/3/5|
|11|secret-handling|secret broker|PH-5|`01E §3.4`; `01K §2.15`|ENV-SANDBOX|no-embed/redaction|PH-5|
|12|network-denial|network broker|PH-5|`01E §3.3`; `PD §13`|ENV-SANDBOX/OFFLINE|network-denial|PH-5|
|13|cache-integrity|cache mgr|PH-5|`01E §3.5`|ENV-SANDBOX|cache-immutability|PH-5|
|14|process-tree termination|sandbox, tool gateway|PH-3/5|`01K §3.1/§3.4`; `01E §3.9`|ENV-SANDBOX|no-orphan|PH-3/5|
|15|failure-path|all|every phase|`01G §4`; `04`; `01O §3.7`|ENV-DEV/SANDBOX|failure-path evidence|phase|
|16|crash & interruption|Orchestrator, journal, Watchdog|PH-2/7|`01M §30`; `01O §3.7`|ENV-DEV/ISO|crash-recovery|RM-1/RM-3|
|17|journal replay|journal|PH-2|`01M §3.6/§2.18`|ENV-DEV|replay-idempotency|PH-2|
|18|fencing-token|lease system|PH-2|`01M §3.6/§2.19`|ENV-DEV|stale-owner-rejection|PH-2|
|19|snapshot-integrity|snapshot mgr|PH-7|`01M §3.9`|ENV-ISO-RESTORE|snapshot-integrity|RM-3|
|20|isolated-restore|snapshot mgr|PH-7|`01M §3.9/§31`|ENV-ISO-RESTORE|candidate-restore|PH-7|
|21|updater & rollback|updater|PH-8|`01O §2.18-30/§3.6`|ENV-CLEAN-WIN|update/rollback|RM-4|
|22|migration|schema&migration|PH-1/8|`01O §2.19/§2.29`|ENV-DEV|transactional-migration|PH-1/8|
|23|installer|installer|PH-8|`01O §2.2-13/§3.3`|ENV-CLEAN-WIN|install evidence|IP-5/stable|
|24|uninstall|installer|PH-8|`01O §2.45-47/§3.8`|ENV-CLEAN-WIN|uninstall-preservation|stable|
|25|offline-operation|Dashboard, control plane|PH-S/4/8|`01L §2.26`; `PD §13`|ENV-OFFLINE|offline-operation|PH-S/4/8|
|26|Windows 11 Home (±act.)|all runtime|every phase + PH-8|`01N`; `01O §2.36-37`|ENV-CLEAN-WIN|Windows-Home evidence|phase+stable|
|27|resource-pressure|Resource Scheduler, Watchdog|PH-3/4|`01J §3.3`; `01M §3.3/§3.10`|ENV-SANDBOX|resource-pressure|PH-3/4|
|28|scheduler|Resource Scheduler|PH-4|`01J §3.3`; `01D §3.5`|ENV-DEV/SANDBOX|scheduler evidence|PH-4|
|29|model-routing|router|PH-4|`01J §2/§5`; `03 §7`|ENV-DEV|no-silent-sub|VM-3|
|30|model-fallback|router, model-exec records|PH-4|`01J §3.2`; `04 §6`|ENV-DEV|fallback-provenance|PH-4|
|31|evidence-integrity|evidence store, ETM|PH-7|`01G §2.18/§3.1`|ENV-DEV|ETM-completeness|VM-5|
|32|audit-chain|audit writer, validator|PH-3|`01K §3.2`|ENV-DEV|chain-break-detection|PH-3|
|33|graph-integrity|graph, repo-index|PH-8|`01P §3.1-3.6/§5`|ENV-DEV|graph-integrity|PH-8|
|34|research-provenance|research system|deferred (Stage 14)|`01Q §3.1/§5`|ENV-SANDBOX/OFFLINE|claim-provenance|post-core|
|35|release-reproducibility|packaging, release ver.|PH-8|`01G §2.20-21`; `01O §3.9`|ENV-CLEAN|reproducible-build|stable|

## Additional coverage
- **Autonomy (Decision A):** autonomy-boundary tests — component permission/approval/Orchestrator; PH-3; `PD §8`+`01R`; ENV-DEV/SANDBOX; autonomy-envelope evidence; PH-3 gate.
- **Deletion (Decision B):** deletion-policy tests (approval-required) under category 9; PH-3.
- **Windows-native exclusion (Decision C):** category 7/26 assert no non-WSL2/Docker execution path; PH-5.
