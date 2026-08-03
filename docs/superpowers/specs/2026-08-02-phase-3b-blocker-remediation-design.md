# Phase 3B Blocker Remediation Design

## Scope

Resolve the six independent-review blockers without changing the public task lifecycle: isolate
worker-controlled verification commands, authenticate approval decisions, wire the local launcher
to the complete Phase 3B service graph, revalidate paths immediately before writes, roll back
interrupted promotions durably, and bound and verify Windows process-tree cleanup.

## Boundaries

- Verification command execution is delegated to an explicit isolated runner. No production
  fallback may execute worker-controlled tests directly on the host; absence or failure of the
  runner fails verification closed.
- Approval and rejection require a session-scoped runtime credential. The server compares it in
  constant time and supplies the configured operator identity; request bodies cannot assert an
  identity. The credential is injected into the browser session at runtime, held in memory only,
  and excluded from source, storage, logs, and repository files.
- The launcher creates ephemeral security and audit database paths, passes the complete Phase 3B
  configuration to the orchestrator, and starts the worker lifecycle service required to process
  queued work. Startup reconciliation runs before the API becomes healthy.
- A successful path decision is revalidated after the model call and immediately before any
  directory creation or write.
- A durable promotion intent records target ref, original revision, and checkpoint before the ref
  can move. Restart reconciliation restores the original revision, records rollback success or
  explicit failure, and leaves the task `FAILED`; it never infers completion.
- Windows cleanup gives `taskkill` a bounded timeout, checks its return code, waits for confirmed
  termination, and raises `StartupFailure` if the process tree cannot be proven gone.

## Verification

Each blocker receives a regression test that fails against the current implementation. Focused
tests run after each minimal fix. After all six pass together, run the complete Linux gate once,
make one commit and push, then run the native-Windows launcher and junction gates at the exact
pushed code SHA. PR #18 remains draft and merge review stays paused until both platforms pass.
