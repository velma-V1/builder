# Phase-Exit Checklist — Template

**Type:** Scaffold (non-authoritative) · **Instance authority:** the per-phase completed checklist is an
L25.1 evidence record. **Governing:** `docs/10 §15` (operator promotion gates), `01G` (verdicts/ETM), the
phase's VEP + CERT. **Placement:** `docs/verification/<phase>-phase-exit-checklist.md`. **Established:**
2026-07-26 (RPH3 Pass 10; gap G-05).

A phase exits only when **every** box is checked with a repository-cited artifact. No box is checked from
memory; each cites a test path, a manifest entry, or a governing section.

## Checklist

```markdown
# <Phase> — Phase-Exit Checklist    Branch/HEAD: ...    Date: ...

## Acceptance
- [ ] Every governing acceptance criterion PASS (<supplement(s)>, N criteria) — evidence: <report §>
- [ ] Integration milestone (VM-x) PASS — evidence: <manifest#>
- [ ] Decisions in force for this phase proven (e.g. Dec A/B) — evidence: <tests>

## Evidence & quality
- [ ] `01G §3.1` ETM chain complete for every requirement (no broken link)
- [ ] Coverage obligation met (≥ ...% branch) — evidence: <manifest#>
- [ ] ruff clean · [ ] mypy --strict clean
- [ ] Regenerable verification manifest present (gitignored)

## Defects & regressions
- [ ] Zero unresolved critical/high defects
- [ ] Every REGR-* seeded this phase cleared (REGRESSION-REGISTER)

## Boundaries
- [ ] Rollback boundary defined + demonstrated
- [ ] No scope absorbed from another phase; external prerequisites recorded as external
- [ ] `main` untouched; no unauthorized merge; roadmap not amended (unless separately approved)
- [ ] Namespace/identifier discipline preserved (no cross-component reuse)

## Promotion
- [ ] Readiness certificate present (CERT-<phase>)
- [ ] Operator phase-exit approval obtained (`docs/10 §15`)
- [ ] Next-phase entry prerequisites confirmed available
```

**Rule:** the checklist is evidence, not authority; it never overrides the governing supplement. Superseded by
pointer, never deleted.
