# WorldMonitor 00 — Overview

WorldMonitor is integrated as a **managed first-class module** and an **external pinned dependency**
(`koala73/worldmonitor`). Its source is **not** copied, forked, or rebranded into Builder. This
package is the Builder-side interface for pinned read-only access, normalization with preserved
provenance, durable lifecycle state, and dashboard presentation.

State: deterministic integration `PASS`; Docker-backed live acceptance `BLOCKED`. Builder builds the
exact external pinned revision, verifies the resulting immutable image identity, and uses only the
verified read-only earthquake contract. Source failures are durably `DEGRADED` and never fabricate
records. `WORLDMONITOR_MODEL_ACCESS := NONE`, `WORLDMONITOR_HOSTED_ACCESS := DISABLED`, and
`WORLDMONITOR_LICENSE := AGPL-3.0-or-later`.
