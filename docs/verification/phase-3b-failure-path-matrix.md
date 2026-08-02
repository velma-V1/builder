# Phase 3B Failure-Path Matrix

| Failure | Expected result | Status |
|---|---|---|
| Verifier raises after worker success | durable `FAILED`, never complete | PASS |
| Required checks or acceptance evidence missing | verification fails closed | PASS |
| Evidence/manifest tampered | read/promotion rejected | PASS |
| Duplicate run diverges | deterministic replay conflict | PASS |
| Approval absent, expired, reused, or misbound | promotion rejected | PASS |
| Target drifts or is protected | rejected before write | PASS |
| Promotion write fails | rollback attempted; durable `FAILED` | PASS |
| Verification interrupted | durable evidence reconciled and artifacts rechecked | PASS |
| Promotion interrupted | fail closed with recovery evidence | PASS |
| UI reconnects | pending approval and durable result refetched | PASS |
| Windows junction escapes project root | denied by contract and Agent Zero policy boundaries | PASS |
| CRLF checkout changes manifest bytes only | canonical LF digest remains stable and validates | PASS |
