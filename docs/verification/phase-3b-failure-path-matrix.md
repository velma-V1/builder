# Phase 3B Failure-Path Matrix

| Failure | Expected result | Status |
|---|---|---|
| Untrusted worker tests execute during verification | isolated process with no host secret, repository-write, or network access | FAIL — verifier invokes host `pytest` without a process sandbox |
| Verifier raises after worker success | durable `FAILED`, never complete | PASS |
| Required checks or acceptance evidence missing | verification fails closed | PASS |
| Evidence/manifest tampered | read/promotion rejected | PASS |
| Duplicate run diverges | deterministic replay conflict | PASS |
| Approval absent, expired, reused, or misbound | promotion rejected | FAIL — API accepts caller-supplied operator identity and destructive confirmation without authentication |
| Target drifts or is protected | rejected before write | PASS |
| Promotion write fails | rollback attempted; durable `FAILED` | PASS |
| Verification interrupted | durable evidence reconciled and artifacts rechecked | PASS |
| Promotion interrupted | fail closed with recovery evidence | FAIL — restart reconciliation can leave an advanced ref applied |
| UI reconnects | pending approval and durable result refetched | PASS |
| Authorized directory becomes a symlink/junction before worker write | revalidate immediately before use and deny escape | FAIL — worker transport does not revalidate before write |
| Windows launcher process-tree cleanup hangs or fails | bounded cleanup and explicit failure evidence | FAIL — `taskkill` has no timeout and its failure is ignored |
| Windows junction escapes project root | denied by contract and Agent Zero policy boundaries | ENVIRONMENT-BLOCKED — historical PASS at `48e0dd8`; exact-head rerun required |
| CRLF checkout changes manifest bytes only | canonical LF digest remains stable and validates | HISTORICAL PASS at `48e0dd8`; not rerun at current head |
