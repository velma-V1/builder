"""Read-only HTTP surface for authoritative task snapshots (Phase 2B, CMP-API).

``GET /api/tasks/snapshot?workstream=<id>`` is the only route. The application factory
accepts an ``OrchestratorStateReader`` explicitly — never a writer — so there is no code
path from this process to a state mutation (R1 remains intact: the Orchestrator's single
writer is never imported here). No connection is opened at import time; the caller
supplies an already-constructed reader (see ``scripts/run_api.py`` for local dev).

Errors never leak internals (file paths, SQL text, stack traces) to the client. Request
validation (missing/blank ``workstream``) stays a distinct 400 outside the failure
boundary below. Everything from "ask the reader for rows" through "map each row to the
wire contract" is one bounded step: any failure there — a SQLite error, a row whose
``current_state`` isn't a known ``TaskState``, an ``updated_at`` that doesn't parse, or
any other authoritative-data/mapping failure — becomes the same fixed 503 JSON body.
Catching ``Exception`` here does not risk swallowing process-control signals:
``KeyboardInterrupt``/``SystemExit``/``GeneratorExit`` all derive from ``BaseException``,
not ``Exception``, so they always propagate.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from factory.api.mapping import to_task_snapshot
from factory.orchestrator.store.runtime_state import OrchestratorStateReader


async def _get_tasks_snapshot(request: Request) -> JSONResponse:
    workstream_id = request.query_params.get("workstream")
    if workstream_id is None or workstream_id.strip() == "":
        return JSONResponse({"error": "workstream query parameter is required"}, status_code=400)

    reader: OrchestratorStateReader = request.app.state.task_reader
    try:
        records = reader.list_tasks_by_workstream(workstream_id)
        snapshot = [to_task_snapshot(record) for record in records]
    except Exception:
        return JSONResponse({"error": "snapshot temporarily unavailable"}, status_code=503)

    return JSONResponse(snapshot)


def create_app(*, task_reader: OrchestratorStateReader) -> Starlette:
    """Narrow application factory: the reader is the only dependency, passed explicitly."""
    app = Starlette(
        routes=[Route("/api/tasks/snapshot", _get_tasks_snapshot, methods=["GET"])],
    )
    app.state.task_reader = task_reader
    return app
