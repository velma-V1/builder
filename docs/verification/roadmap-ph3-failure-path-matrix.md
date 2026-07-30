# Roadmap PH-3 Complete Failure-Path Matrix

| Failure/abuse path | Required outcome | Evidence | Verdict |
|---|---|---|---|
| Permission bypass/revocation | deny | T2 + cross-lane security | PASS |
| Approval bypass/expiry/replay/cross-operation token | deny | T3 + approval/cross-lane tests | PASS |
| Unregistered tool/unsafe arguments/gateway bypass | deny | T5 tool security/failure tests | PASS |
| Path escape/symlink/TOCTOU swap | deny or classified platform skip | T2/T5 + contracts path tests | PASS |
| Raw writer/cross-domain write | SQLite authorizer denial | T1-T5 isolation tests | PASS |
| Audit tamper/store failure | non-authoritative; contain/fail closed | T4 + cross-lane failure tests | PASS |
| Spoofed Watchdog heartbeat/WIR request | reject | T1 security tests | PASS |
| Unauthorized/stale/unbounded recovery | reject without effect | T1 + cross-lane security tests | PASS |
| Crash before/after Watchdog record or WIR delivery | reconcile; no duplicate effect | T1 crash-window suite | PASS |
| Crash before/after Lane B result | reconcile or terminal fail closed | Lane B crash suites + cross-lane replay | PASS |
| Duplicate/conflicting/partial result | prior result or explicit failure | cross-lane concurrency/failure tests | PASS |
| Approval/permission/watchdog store failure | explicit domain failure | component failure-path suites | PASS |
| Safe Mode dependency failure | read-only fail-closed session | T5 + cross-lane tests | PASS |
| Fresh/existing/failed/tampered migration | apply idempotently or reject/rollback | component store + portability tests | PASS |
| SQLite connection leak regression | no `ResourceWarning` under error policy | integrated verifier warning gate on 3.12/3.13/3.14 | PASS |
