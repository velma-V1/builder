# Component Specification — Tool Gateway (CMP-TOOLGW)

**Instance authority:** L25.1 planning record · **Phase:** roadmap PH-3 (RPH3-T5) · **Governing:** `01K`
(§2.1-2/§2.25/§3.1/§3.4, acceptance #1/#13/#14/#25). Parent index:
`docs/specifications/components/00-COMPONENT-MAP.md` #10. Baselines inherited; only deltas stated.

```yaml
component_id:          CMP-TOOLGW
name:                  Tool Gateway
implementation_phase:  PH-3 (RPH3-T5)
responsibility: >
  The single controlled path through which any approved tool is invoked. Before a call it confirms the tool
  is registered (CMP-TOOLREG, default-deny) and the action is permitted (CMP-PERM grant, revalidated); it
  applies mandatory execution resource controls (wall-clock/idle/CPU/RAM/storage/process/file-count/output/
  log/download limits + complete process-tree tracking and termination); and it treats all tool OUTPUT as
  untrusted, schema-validating it before any consumer sees it. Models cannot bypass the gateway.
non_responsibilities:
  - Does not register tools (CMP-TOOLREG) or decide base permissions/approvals (CMP-PERM/CMP-APPROVAL).
  - Does not itself provide the sandbox (PH-5) — it enforces the resource/termination contract at the seam.
  - Does not write audit records directly beyond calling CMP-AUDITW for privileged calls.
authoritative_state:   none for state (R1); emits tool-execution + resource-breach events (audited).
inputs:
  - tool-call request (tool_id, version, args, task context)
  - registry lookup (CMP-TOOLREG) + permission grant (CMP-PERM)
  - raw tool output stream (untrusted)
outputs:
  - validated tool result (schema-checked) OR denial/quarantine signal
  - resource-limit + process-tree termination actions
  - audit records for privileged/credentialed/external/destructive calls (via CMP-AUDITW)
interfaces:
  - "ToolGateway.invoke(call: ToolCall) -> ToolResult | Denial"
  - "ToolGateway.validate_output(raw, declared_schema) -> ValidatedOutput   # untrusted until validated"
  - "ToolGateway.enforce_limits(exec_ctx) -> ResourceVerdict                 # 01K §3.1 caps"
  - "ToolGateway.terminate_tree(exec_ctx) -> None                            # complete process-tree kill"
dependencies:
  - CMP-TOOLREG (is-registered + declaration; default-deny on miss)
  - CMP-PERM (least-privilege grant + TOCTOU revalidation at call time)
  - CMP-FILEOP (file-touching tool actions route through the safe file-op service)
  - CMP-AUDITW (privileged/credentialed/external/destructive calls are audited)
owned_contracts:       [ ] (enforces CTR-TOOL-DECLARATION + CTR-PERMISSION-GRANT; owns none)
permitted_authority:   BASE-P; invokes only registered + permitted tools with pinned versions; every
                       execution is resource-bounded with complete process-tree control (01K §3.1).
prohibited_authority:  BASE-X + provides no bypass path; an unregistered or unpermitted call is denied; raw
                       output is never passed through unvalidated.
trust_boundary:        BASE-T; tool output is Zone-untrusted (validated for schema/integrity/freshness/scope/
                       task-relevance before use, 01K §2.25); a model cannot reach a tool except via invoke().
failure_modes:
  - unregistered/unpermitted call -> denied (default-deny)
  - output schema-validation failure -> rejected, not delivered
  - resource limit/idle/timeout breach -> terminate complete process tree, revoke creds, quarantine sandbox
  - repeated equivalent failure -> signal CMP-TOOLREG to quarantine the tool
degradation_behavior:  BASE-D; gateway/limit failure fails closed (no tool runs unbounded).
recovery_behavior:     BASE-R; abnormal termination leaves no orphan process (process-tree kill); evidence
                       preserved before disposal when safe; sandbox quarantined if cleanup uncertain.
security_requirements: BASE-S; single-path + default-deny + output validation + resource/process-tree control
                       are core controls; no-bypass is a security invariant.
resource_requirements: BASE-RES; enforces the per-execution resource envelope; the gateway itself is light.
required_tests:
  - no bypass: a model/tool cannot execute an unregistered tool or reach one except via the gateway (01K-AC-01)
  - output validation: malformed/oversized/out-of-scope output fails closed (01K-DEC-25 "untrusted output";
    NOT 01K-AC-25 which is telemetry)
  - resource-limit REQUEST CONTRACT defined + fail-closed when unenforceable (01K-AC-13 request part; actual
    OS enforcement = PH-5 gate EG-PH5-04)
  - termination REQUEST CONTRACT defined; **fail-closed when no valid sandbox executor exists**. Actual
    complete process-tree termination + no-orphan are **PH-5 enforcement** (01K-AC-14/15 → EG-PH5-05/06);
    RPH3 proves only that no direct host execution occurs here (see XIB-02)
  - a limit increase is treated as a permission change (routes to CMP-PERM/CMP-APPROVAL, 01K §3.1)
```

## Lifecycle

- **Initialization:** wire to CMP-TOOLREG + CMP-PERM + CMP-FILEOP + CMP-AUDITW; load the resource-limit policy.
- **Runtime:** invoke → registry check → permission revalidate → apply resource envelope → run at the sandbox
  seam → validate output → deliver or deny; on breach, terminate the process tree and quarantine.
- **Recovery:** no orphan survives; evidence finalized before disposal when safe.

## No-bypass note

CMP-TOOLGW is the *only* runtime tool-call path; combined with CMP-TOOLREG default-deny it guarantees no
model/plugin/task executes a tool outside governing permission/resource/audit rules. Recorded in `RPH3-INTEGRATION.md`.
