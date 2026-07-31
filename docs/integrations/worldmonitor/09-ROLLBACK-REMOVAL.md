# WorldMonitor 09 — Rollback / Removal

Reverse of install (each phase has a declared rollback): stop_later → remove_later removes the
service + volumes + dedicated network; rollback_later restores the prior pinned revision. Revoke any
`WORLDMONITOR_*` secret from the `SecretBroker`. Clear caches per retention. Reverting the PR removes
the Builder-side interface entirely; the external dependency is simply not deployed.
