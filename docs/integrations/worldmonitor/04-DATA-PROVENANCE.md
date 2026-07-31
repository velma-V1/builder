# WorldMonitor 04 — Data & Provenance

WorldMonitor data is an **external claim**, attributed to its source — never Builder truth. Each
`IntelligenceRecord` carries: preserved `raw_reference` + `WorldMonitorSourceRef`; a `content_digest`;
an immutable `provenance_chain` (source → fetch → normalize → ai); and `confidence` **only** when the
source supplied it (never invented). Stale data is visibly marked (`Freshness.STALE`), not dropped.
Dedup is by stable source identity + digest. Malformed timestamps/geography and source URLs outside
the approved domains fail closed.
