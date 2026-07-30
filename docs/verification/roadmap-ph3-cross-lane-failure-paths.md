# RPH3 Cross-Lane Failure-Path Matrix

| Failure | Required result | Test | Verdict |
|---|---|---|---|
| Permission denied/revoked | terminal DENIED; no recovery effect | permission + FileOp tests | PASS |
| Approval required | explicit APPROVAL_REQUIRED, never success | permission/approval tests | PASS |
| Approval expired or consumed/replayed | terminal DENIED | approval lifecycle test | PASS |
| Tool unregistered/gateway denial | terminal DENIED, no bypass | ToolGateway test | PASS |
| FileOp permission denial | terminal DENIED | FileOp test | PASS |
| Audit chain break | WIR containment, completion-audited before INTERVENED | audit-break test | PASS |
| Audit validator unavailable | fail closed through containment | validator-outage test | PASS |
| Dependency unavailable | WIR pause | dependency-failure test | PASS |
| WIR stale expected state | DENIED, never implicit success | stale-delivery test | PASS |
| WIR unavailable | explicit FAILED terminal result | WIR-outage test | PASS |
| Safe Mode required | read-only capability declaration; no autonomous write | Safe Mode escalation test | PASS |
| Duplicate message | same prior result; one intervention effect | duplicate + restart-replay tests | PASS |
| Conflicting duplicate | explicit FAILED | conflict test | PASS |
| Missing/wildcard/unbounded target | explicit FAILED before delivery | security tests | PASS |
| Concurrent domain messages | independent terminal results | concurrent-domain test | PASS |
| Crash before/after WIR commit | replay through durable WIR result; no duplicate effect | restart-replay test plus T1 crash-window suite | PASS |
