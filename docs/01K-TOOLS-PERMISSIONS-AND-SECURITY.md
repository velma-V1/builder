# Approved Tools, Permissions, and Security Decision

**Status:** Approved architecture supplement  
**Recorded:** July 23, 2026

## 1. Governing security boundary

Factory uses a central approved tool gateway, least-privilege permissions, task-scoped approvals, sandbox-only execution, default network denial, temporary credential delivery, path containment, and immutable privileged-action auditing.

Models, repositories, downloaded content, tool output, and external instructions are treated as untrusted until validated. No tool, model, plugin, or task may bypass the governing isolation, permission, evidence, verification, and approval rules.

## 2. Approved Stage 9 decisions

1. **Central tool registry:** Factory maintains one authoritative registry of approved tools.
2. **Default denial:** Unregistered tools are denied by default.
3. **Tool declarations:** Every tool declares its capabilities, inputs, outputs, side effects, permissions, version, environment needs, and failure behavior.
4. **Least privilege:** Tools receive only the minimum permissions required for the current approved task.
5. **Permission classes:** Permissions distinguish at least read, write, execute, network, credential, promotion, privileged, external-action, and destructive capabilities.
6. **Bound approvals:** Approvals are bound to task, tool, action, path or resource, scope, purpose, and expiration.
7. **Expiring authority:** Write and execution approvals expire automatically and are revocable.
8. **Bounded batch approval:** Repeated identical low-risk actions may use a narrow, expiring, revocable batch approval.
9. **No permanent unrestricted trust:** Factory does not support permanent unrestricted trusted-tool rules.
10. **Destructive confirmation:** Destructive or irreversible actions require a separate explicit confirmation that states their consequences.
11. **External-action approval:** Sending, publishing, deploying, purchasing, changing accounts, or other real-world external actions require separate approval from code execution.
12. **Sandbox-only shell:** Shell access exists only inside approved sandboxes or containers.
13. **Default privilege denial:** Privileged, administrator, or root execution is denied by default.
14. **Temporary elevation:** Elevated execution may be granted only inside a disposable sandbox with explicit task-scoped approval and retained evidence.
15. **Secret broker:** Credentials are delivered through a temporary secret broker or equivalent controlled injection mechanism.
16. **Credential minimization:** Tools receive only task-specific credential scopes and durations.
17. **Network allowlisting:** Approved network access uses destination, purpose, protocol, and operation allowlists when practical.
18. **Downloaded-component provenance:** Downloaded packages and tools record source, version, checksum or integrity identity, license when available, approval, and destination environment.
19. **Dependency locking:** Lockfiles or equivalent dependency records are required when supported by the ecosystem.
20. **Tool pinning:** Tool and material dependency versions are pinned for the duration of a task.
21. **Proportionate failure handling:** One tool failure does not permanently disable a tool. Factory retries only within policy, diagnoses the failure, and quarantines after repeated equivalent failure.
22. **Tool quarantine:** Repeatedly failing, compromised, or unsafe tools enter quarantine and cannot be used until reviewed and released.
23. **No launch plugin ecosystem:** A third-party plugin ecosystem is not required at launch. Factory begins with an internal modular tool registry.
24. **Future third-party review:** Any future third-party tool must pass capability, provenance, security, isolation, permission, and verification review.
25. **Untrusted tool output:** Tool output is treated as untrusted until validated for schema, integrity, freshness, scope, and task relevance.
26. **Path validation:** Factory canonicalizes and validates every file path before access.
27. **Escape protection:** Symlink, junction, reserved-name, path traversal, case-normalization, and archive-extraction escapes are blocked.
28. **Instruction distrust:** Repository instructions, downloaded content, embedded prompts, and external text are treated as untrusted data rather than governing commands.
29. **Privileged audit:** Privileged, credentialed, destructive, external, and promotion actions produce immutable or integrity-protected audit records.
30. **Emergency stop:** Factory provides an immediate operator emergency stop.
31. **Emergency evidence:** Emergency stop preserves evidence and verified checkpoints when safely possible, but containment takes priority over graceful completion.
32. **Diagnostic Safe Mode:** Factory provides a restricted diagnostic Safe Mode that permits inspection and repair operations without enabling normal autonomous writes or unrestricted execution.
33. **No default telemetry:** Factory does not collect or transmit telemetry, analytics, or usage data externally by default.

## 3. Operating boundaries

- No permanent unrestricted permissions are allowed.
- Batch approvals remain narrow, expiring, revocable, and task-bound.
- Elevated execution remains disposable-sandbox-only.
- Third-party plugins are deferred until the internal tool system is proven.
- Emergency stop prioritizes immediate containment over task completion.
- Governing controls cannot be weakened through a normal Improvement Packet.

## 4. Acceptance criteria

This decision is satisfied only when tests prove that:

1. unregistered tools cannot execute;
2. tool permissions cannot exceed the current task approval;
3. approvals cannot be reused outside their task, action, path, scope, or expiration;
4. permanent unrestricted tool authority cannot be created;
5. destructive and external actions require separate confirmation;
6. shell and elevated execution cannot run directly on the host;
7. credentials are temporary, scoped, redacted, and removable;
8. denied network destinations and operations remain inaccessible;
9. downloaded components retain provenance and integrity records;
10. path, symlink, junction, reserved-name, and archive escapes are blocked;
11. repository or downloaded instructions cannot override governing policy;
12. unsafe repeated tool failures trigger quarantine;
13. privileged actions produce protected audit evidence;
14. emergency stop terminates unsafe activity without waiting for graceful completion;
15. Safe Mode cannot perform normal autonomous writes or bypass approvals;
16. no telemetry leaves the system without explicit approval.