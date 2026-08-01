# Builder UI Studio — frontend

**Status: PHASE_1_DASHBOARD_RUNNABLE_LOCALLY.** Real dependencies are installed and pinned to exact,
registry-resolved versions (`package.manifest.json` + `package.json` + `package-lock.json` — never
guessed; see the PR description on `claude/ui-activation-phase-1` for how each major version was
selected). The dashboard builds, type-checks, lints, and renders. No live backend connection is
opened: Agent Zero is not activated, no model or Ollama connection exists, and no real WebSocket/SSE
transport is opened — the real-time client, task snapshot, and dev fixture data are all local/mocked.

## Install and run

```bash
cd ui
npm ci              # clean install from package-lock.json
npm run dev         # http://localhost:1420
```

Other scripts:

```bash
npm run build        # production build -> ui/dist/
npm run typecheck    # tsc --noEmit
npm run test         # vitest run
npm run test:watch   # vitest, watch mode
npm run lint         # eslint .
npm run test:e2e     # playwright test (needs `npx playwright install chromium` once)
npm run storybook    # Storybook dev server
```

## Why this exists

This is the frontend half of `src/factory/ui_studio/`. The backend package compiles a requirement
into a generation plan and renders it through a deterministic fake renderer; this directory is a
representative, hand-written instance of what that plan looks like as real source — one composition
per architectural concern, not 16 duplicated applications. The 16 UI Studio templates are backend
descriptors (`factory.ui_studio.template_registry`) whose artifacts are asserted complete by
`scripts/verify_ui_studio_structure.py`, not by shipping 16 copies of this scaffold. Only the
Builder Command Center dashboard (`src/pages/Dashboard.tsx`) is wired into the rendered app in this
phase; the chart/diagram/map/3D/editor components exist, type-check, and bundle correctly (verified
by temporarily importing all of them together during Phase 1 activation) but aren't yet routed to a
page of their own.

## State boundaries (enforced on the backend, mirrored here)

| Owner | Where | What |
|---|---|---|
| XState | `src/state/*.machine.ts` | Workflows and legal transitions only — never authoritative truth |
| TanStack Query | `src/queries/*.ts` | Backend snapshots and records, bounded by a staleness window |
| Zustand | `src/stores/*.ts` | Presentation-only state (sidebar, active tab, etc.) |
| Backend | `factory.orchestrator` (not in `ui/`) | All authoritative state |

`factory.ui_studio.state_contracts` / `data_contracts` enforce this boundary on the backend side
(a `ZUSTAND_PRESENTATION` contract may not declare a `query_key` or a backend-shaped field; an
`XSTATE_WORKFLOW`/`TANSTACK_QUERY_SNAPSHOT` contract may never claim to be authoritative). Phase 1
does not change this boundary: `useTaskSnapshot` still only ever reads what `fetchTaskSnapshot`
returns (mocked with deterministic fixtures in tests, and empty/backend-shaped in the dev app since
no backend is running), and the sidebar store still only ever holds presentation state.

## Real-time layer

`src/realtime/client.ts` is the client-side mirror of `factory.ui_studio.realtime_contracts` — same
guarantees, same shape: monotonic sequence numbers, idempotent duplicate events, out-of-order
rejection, gap detection (`detectMissingSequence()`/`assertNoMissingSequence()`, mirroring the
backend's end-of-batch judgment rather than rejecting every out-of-sequence arrival immediately),
bounded replay, reconnect cursors, snapshot reconciliation, stale-state indicators, and no
client-invented authoritative state. No WebSocket/SSE connection is opened anywhere in this
repository state — `openTransport()` only selects a transport class.

## Layout

```
ui/
  package.json, package-lock.json   real, installed dependency set — exact pinned versions
  package.manifest.json    approved technology profile, cross-checked against package.json by
                            scripts/verify_ui_studio_structure.py
  tsconfig.json, vite.config.ts, tailwind.config.ts, eslint.config.ts   build/lint config
  vitest.config.ts, playwright.config.ts, .storybook/main.ts   test/docs config
  src-tauri/tauri.conf.json   desktop shell config (not built; bundle.active = false — untouched)
  src/
    main.tsx, App.tsx        entry
    index.css                Tailwind v4 entry point (@config + @import "tailwindcss")
    tokens/                  design tokens (mirrors factory.ui_studio.design_tokens)
    state/                   XState machines
    queries/                 TanStack Query hooks
    stores/                  Zustand stores
    realtime/                real-time client (WebSocket + SSE fallback, neither opened)
    api/                     snapshot fetch (recovery path for reconciliation)
    components/ui/           shadcn/ui-style primitives
    components/charts/       Apache ECharts
    components/diagrams/     React Flow
    components/maps/         MapLibre + deck.gl
    components/three/        React Three Fiber
    components/motion/       Motion
    components/editor/       Monaco
    pages/                   template pages
    __tests__/               Vitest + Testing Library (includes a full App/Dashboard render test)
  e2e/                       Playwright + axe-core
  stories/                   Storybook
```

## Not done in this phase

Agent Zero activation, model/Ollama connections, voice/wake word, Tauri bundling, and any live
WebSocket/SSE/backend connection are all explicitly out of scope for `claude/ui-activation-phase-1`
and are untouched.
