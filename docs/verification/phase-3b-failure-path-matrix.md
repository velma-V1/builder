# Phase 3B Failure-Path Matrix

| Failure | Expected result | Status |
|---|---|---|
| Untrusted worker tests execute during verification | isolated process with no host secret, repository-write, or network access | PASS — isolated runner is mandatory and regression tested |
| Verifier raises after worker success | durable `FAILED`, never complete | PASS |
| Required checks or acceptance evidence missing | verification fails closed | PASS |
| Evidence/manifest tampered | read/promotion rejected | PASS |
| Duplicate run diverges | deterministic replay conflict | PASS |
| Approval absent, expired, reused, or misbound | promotion rejected | PASS — runtime session authenticates requests and operator identity is server-derived |
| Target drifts or is protected | rejected before write | PASS |
| Promotion write fails | rollback attempted; durable `FAILED` | PASS |
| Verification interrupted | durable evidence reconciled and artifacts rechecked | PASS |
| Promotion interrupted | fail closed with recovery evidence | PASS — durable intent drives restart rollback or explicit rollback failure |
| UI reconnects | pending approval and durable result refetched | PASS |
| Authorized directory becomes a symlink/junction before worker write | revalidate immediately before use and deny escape | PASS — authority is revalidated immediately before transport write |
| Windows launcher process-tree cleanup hangs or fails | bounded cleanup and explicit failure evidence | PASS — timeout, return code, and process exit are verified; native-Windows focused gate 8/8 |
| Windows junction escapes project root | denied by contract and Agent Zero policy boundaries | PASS — exact-commit native-Windows gate 2/2 |
| CRLF checkout changes manifest bytes only | canonical LF digest remains stable and validates | HISTORICAL PASS at `48e0dd8`; not rerun at current head |
