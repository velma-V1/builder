# Verification Report — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** the per-phase report is an L25.1 evidence
record. **Governing:** `01G` (verdicts + ETM); the phase's VEP plan. **Placement:**
`docs/verification/<phase>-evidence-report.md`. **Established:** 2026-07-26 (RPH3 Pass 6; gap G-06 — generalizes
the Section-1 report into a reusable template).

## Required sections

```markdown
# <Phase> — Verification Evidence Report

**Phase / component:** ...        **Branch / HEAD:** ...        **Date:** ...
**Governing acceptance:** <supplement(s) + criteria count>     **Verdict:** PASS | FAIL | BLOCKED | INCONCLUSIVE

## 1. Environment table (actuals, not planning envelopes)
| Field | Value | Notes |
|---|---|---|
| OS / runtime | ... | native-Windows deltas recorded as known limitations |
| Tooling pins | ... | uv.lock / pyproject |
| Coverage | ...% branch | obligation vs actual |

## 2. Requirement → test → verdict → evidence (ETM, 01G §3.1)
| Requirement (VR/criterion) | Test(s) | Verdict | Evidence artifact |
|---|---|---|---|
| ... | tests/... | PASS | artifacts/verification/<phase>/manifest.json#... |

## 3. Test-suite summary
| Category | Count | Passed | Notes |
|---|---|---|---|
| unit / integration / security / adversarial / failure-path / regression | ... | ... | ... |

## 4. Static quality gates
ruff: ... · mypy --strict: ... · coverage: ...% (obligation ≥ ...%)

## 5. Defects & regressions
Open critical/high: ... (must be zero for PASS). REGR-* cleared: ...

## 6. Reproduction
Command: `uv run python3.12 scripts/verify_<phase>.py` → exit 0; regenerable manifest path (gitignored).

## 7. Promotion readiness
Gate (`PROM-<phase>`) criteria checklist: [ ] each acceptance set PASS · [ ] integration milestone (VM-x) ·
[ ] ETM complete · [ ] coverage · [ ] zero critical/high · [ ] operator approval pending/received.
```

**Rules:** every technical claim cites a repository artifact (a test path + a manifest entry). The report is
evidence, not authority — it never overrides the governing supplement. Superseded by pointer, never deleted.
