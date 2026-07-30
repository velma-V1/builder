# Roadmap PH-3 Remaining Risk Register

| Risk/boundary | Classification | Disposition |
|---|---|---|
| Windows symlink attack case cannot create a symlink under current privilege policy | non-blocking, explicitly `NOT_TESTABLE` | retain skip classification and alternate path-authority security tests |
| Actual sandbox process-tree termination, orphan prevention, credential/network enforcement | out of RPH3 scope; PH-5 gate | RPH3 provides request contracts and fails closed without a valid executor |
| Snapshot activation and evidence/promotion enforcement | out of RPH3 scope; PH-7 gate | Watchdog command remains inert until the owning phase exists |
| PR #10 worker substrate | independent draft/unmerged work | leave unmodified; separate operator decision |
| `PROM-RPH3` | operator-owned decision | do not set or infer from implementation verification |

No critical/high implementation defect is recorded. The Windows matrix and fresh-checkout integrity
checks are complete. The remaining rows are explicit future-phase or operator-owned boundaries.
