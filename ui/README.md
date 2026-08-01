# Builder UI Studio — frontend scaffold

**Status: STRUCTURE_COMPLETE_NOT_INSTALLED.** Nothing under this directory has been installed, built,
or run. There is no lockfile, no `node_modules/`, and no dependency version has been guessed —
`package.manifest.json` lists every technology by name with `pinned_version` set to the sentinel
`UNVERIFIED_PENDING_OPERATOR_PIN` until an operator confirms and pins an exact version.

## Why this exists

This is the frontend half of `src/factory/ui_studio/`. The backend package compiles a requirement
into a generation plan and renders it through a deterministic fake renderer; this directory is a
representative, hand-written instance of what that plan looks like as real source — one composition
per architectural concern, not 16 duplicated applications. The 16 UI Studio templates are backend
descriptors (`factory.ui_studio.template_registry`) whose artifacts are asserted complete by
`scripts/verify_ui_studio_structure.py`, not by shipping 16 copies of this scaffold.

## State boundaries (enforced on the backend, mirrored here)

| Owner | Where | What |
|---|---|---|
| XState | `src/state/*.machine.ts` | Workflows and legal transitions only — never authoritative truth |
| TanStack Query | `src/queries/*.ts` | Backend snapshots and records, bounded by a staleness window |
| Zustand | `src/stores/*.ts` | Presentation-only state (sidebar, active tab, etc.) |
| Backend | `factory.orchestrator` (not in `ui/`) | All authoritative state |

`factory.ui_studio.state_contracts` / `data_contracts` enforce this boundary on the backend side
(a `ZUSTAND_PRESENTATION` contract may not declare a `query_key` or a backend-shaped field; an
`XSTATE_WORKFLOW`/`TANSTACK_QUERY_SNAPSHOT` contract may never claim to be authoritative).

## Real-time layer

`src/realtime/client.ts` is the client-side mirror of `factory.ui_studio.realtime_contracts` — same
guarantees, same shape: monotonic sequence numbers, idempotent duplicate events, out-of-order
rejection, gap detection, bounded replay, reconnect cursors, snapshot reconciliation, stale-state
indicators, pending optimistic commands until backend confirmation, restart reconstruction, and no
client-invented authoritative state. No WebSocket/SSE connection is opened anywhere in this
repository state — `openTransport()` only selects a transport class.

## Layout

```
ui/
  package.manifest.json   technology profile — no lockfile, no guessed exact version
  tsconfig.json, vite.config.ts, tailwind.config.ts   build config (not run)
  vitest.config.ts, playwright.config.ts, .storybook/main.ts   test/docs config (not run)
  src-tauri/tauri.conf.json   desktop shell config (not built; bundle.active = false)
  src/
    main.tsx, App.tsx        entry
    tokens/                  design tokens (mirrors factory.ui_studio.design_tokens)
    state/                   XState machines
    queries/                 TanStack Query hooks
    stores/                  Zustand stores
    realtime/                real-time client (WebSocket + SSE fallback)
    api/                     snapshot fetch (recovery path for reconciliation)
    components/ui/           shadcn/ui-style primitives
    components/charts/       Apache ECharts
    components/diagrams/     React Flow
    components/maps/         MapLibre + deck.gl
    components/three/        React Three Fiber
    components/motion/       Motion
    components/editor/       Monaco
    pages/                   template pages
    __tests__/               Vitest + Testing Library
  e2e/                       Playwright + axe-core
  stories/                   Storybook
```

## Activation (not performed here)

Installing dependencies, pinning exact versions, running a build, starting a preview server, or
opening a live WebSocket/SSE connection are all explicitly out of scope for this branch. An operator
performs those steps after reviewing `package.manifest.json` and pinning real versions.
