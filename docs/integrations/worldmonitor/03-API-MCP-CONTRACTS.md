# WorldMonitor 03 — API / MCP Contracts

**REST:** `WorldMonitorRestClient` issues read-only `GET` per category against documented paths. The
official pinned OpenAPI is used **when verified**; until then `OPENAPI_CLIENT_STATUS := BLOCKED_UNVERIFIED`
— no schema is fabricated; the client operates on an interface + fixtures. A generated client (later)
lands in an isolated generated directory and is never hand-edited.

**MCP:** `mcp_client` prepares discovery of the server card, OAuth metadata, tool list, scopes, and
capability flags via a fake transport only. **No** OAuth registration, login, token acquisition, or
live connection. Tool results (later) flow through the same IntelligenceRecord normalization.

**Modes:** `LOCAL_MANAGED_UI` (default future), `LOCAL_REST`, `HOSTED_REST` (disabled), `HOSTED_MCP`
(disabled). Never assume a mode exposes a capability — discover it; unknown ⇒ denied.
