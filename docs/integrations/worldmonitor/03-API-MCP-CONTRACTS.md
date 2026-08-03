# WorldMonitor 03 — API / MCP Contracts

**HTTP:** `WorldMonitorOfficialClient` uses the verified pinned SeBuf route
`/api/seismology/v1/list-earthquakes`. It accepts only the configured loopback WorldMonitor origin,
validates response shape and source identity, and normalizes real USGS records with provenance.
Malformed replies, unexpected hosts, and unavailable sources fail closed; no speculative endpoint
or fabricated fallback record exists.

`mcp_client` remains a non-production discovery contract. It is not used by the implemented refresh
path and cannot become a hidden fallback.

Hosted REST/MCP modes are disabled. This approval covers local managed use only.
