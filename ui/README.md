# Builder UI Studio — frontend

**Status: PHASE_2B_READONLY_SNAPSHOT_API.** Real dependencies are installed and pinned to exact,
registry-resolved versions (`package.manifest.json` + `package.json` + `package-lock.json` — never
guessed; see the PR description on `claude/ui-activation-phase-1` for how each major version was
selected). The dashboard builds, type-checks, lints, and renders. Agent Zero is not activated, no
model or Ollama connection exists, and no real WebSocket/SSE transport is opened. As of Phase 2B,
`GET /api/tasks/snapshot?workstream=<id>` is served by a real, read-only backend (see
`../scripts/run_api.py`) instead of dev-fixture data — see "Phase 2 — read-only backend" below.

## Install and run

```bash
cd ui
npm ci              # clean install from package-lock.json
npm run dev         # http://localhost:1420
```

## Phase 2 — read-only backend

The dashboard's task snapshot now comes from a real (but read-only) backend. Schema setup is a
separate, explicit step from serving: `scripts/run_api.py` never migrates the database itself —
it only ever opens a read-only connection, and fails clearly (pointing at the setup command
below) if the schema is missing or out of date. Three steps, from the repo root:

```bash
cd /home/xxthatguyxx/builder

# 1. Explicit database setup (once, or again after a new migration is added)
uv run python scripts/setup_api_database.py     # applies pending migrations to runtime.db

# 2. Read-only snapshot API — read-only end to end, never touches migrations
uv run python scripts/run_api.py                # http://127.0.0.1:8000

# 3. Vite dev server (from ui/), proxies /api/* to the API above
cd ui
npm run dev                                      # http://localhost:1420
```

`vite.config.ts` proxies `/api/*` to `http://127.0.0.1:8000` by default (override with the
`VITE_API_PROXY_TARGET` env var for a non-default local port). The frontend's fetch path is
unchanged: `GET /api/tasks/snapshot?workstream=<id>`. With no tasks yet assigned to a given
workstream, the endpoint correctly returns `[]` — that's expected, not an error.

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

Agent Zero activation, model/Ollama connections, voice/wake word, Tauri bundling, any live
WebSocket/SSE connection, and any write/mutation API remain explicitly out of scope through
Phase 2B and are untouched. The read-only snapshot endpoint added in Phase 2B is HTTP polling
only — no realtime transport exists on the backend.
