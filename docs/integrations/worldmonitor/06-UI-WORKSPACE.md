# WorldMonitor 06 — UI Workspace

Builder-side **contract only** — no duplicate map is built. The workspace is an embedded webview or a
managed external window with: health + version indicators, start/stop controls **prepared but
disabled**, open/fullscreen/reload, a view-command bridge, a source/provenance side panel, and
stale/offline + permission states.

View commands: `focus_region`, `open_country`, `enable_layer`, `disable_layer`, `open_panel`,
`show_event`, `reset_view`. **UI security:** strict origin allowlist; typed + versioned messages;
unknown types rejected; arbitrary URLs rejected; navigation outside the approved origin blocked; no
arbitrary JS execution; no filesystem bridge; no secret-bearing messages. CSP: default-deny;
`connect/img/script` restricted to the approved workspace origin; `frame-ancestors` limited to
Builder.
