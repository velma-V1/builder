"""Write-authorized HTTP surface for task intake (Phase 3A, CMP-ORCH-API).

Exactly four routes: submit, detail, cancel, health. No approve/reject route exists — nothing
can legitimately be approved before a real worker produces results (Phase 3B/3C).

Mirrors ``factory.api.app``'s controlled-error-response discipline exactly: request validation
(missing/malformed fields) is a distinct 400, raised *before* the failure boundary below. The
read/write/map step for each route is the only thing inside a narrow ``try/except`` — an
``OrchestratorApiError`` becomes its mapped status (404 task-not-found, 409 rejected action,
503 orchestrator-unavailable); any other exception becomes the same fixed 503 JSON body. No
exception text, SQL, paths, or stack traces are ever returned to the client.
"""

from __future__ import annotations

import contextlib
from typing import Any, cast

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from factory.orchestrator.models import TaskRuntimeRecord
from factory.orchestrator_api.errors import OrchestratorApiError
from factory.orchestrator_api.lifecycle import Phase3BLifecycleService
from factory.orchestrator_api.service import TaskDetail, TaskOperatorService

_DEFAULT_SUBMITTED_BY = "operator"
_DEFAULT_CANCEL_REASON = "operator_cancelled"

_ERROR_STATUS = {
    "TASK_NOT_FOUND": 404,
    "ACTION_REJECTED": 409,
    "ORCHESTRATOR_UNAVAILABLE": 503,
}


def _error_response(exc: OrchestratorApiError) -> JSONResponse:
    status = _ERROR_STATUS.get(exc.code, 503)
    if status == 503:
        body = {"error": "orchestrator temporarily unavailable"}
    else:
        body = {"error": exc.message}
    return JSONResponse(body, status_code=status)


def _bad_request(message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=400)


async def _submit_task(request: Request) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")

    required = ("project_ref", "workstream_id", "description", "idempotency_key")
    invalid = [
        field
        for field in required
        if not isinstance(body.get(field), str) or not body[field].strip()
    ]
    if invalid:
        return _bad_request(f"missing or invalid required field(s): {', '.join(invalid)}")

    service: TaskOperatorService = request.app.state.service
    try:
        result = service.submit(
            project_ref=body["project_ref"],
            workstream_id=body["workstream_id"],
            description=body["description"],
            priority=str(body.get("priority") or "normal"),
            model_preference=body.get("model_preference"),
            expected_result=body.get("expected_result"),
            submitted_by=str(body.get("submitted_by") or _DEFAULT_SUBMITTED_BY),
            idempotency_key=body["idempotency_key"],
        )
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)

    return JSONResponse(
        {"task_id": result.task_id, "state": result.state.value, "created": result.created},
        status_code=201 if result.created else 200,
    )


def _task_to_json(record: TaskRuntimeRecord) -> dict[str, Any]:
    return {
        "task_id": record.task_id,
        "project_id": record.project_id,
        "workstream_id": record.workstream_id,
        "state": record.current_state.value,
        "updated_at": record.updated_at,
    }


def _detail_to_json(detail: TaskDetail) -> dict[str, Any]:
    body = _task_to_json(detail.task)
    if detail.request is None:
        body.update(
            description=None,
            priority=None,
            model_preference=None,
            expected_result=None,
            submitted_by=None,
            submitted_at=None,
        )
    else:
        body.update(
            description=detail.request.description,
            priority=detail.request.priority,
            model_preference=detail.request.model_preference,
            expected_result=detail.request.expected_result,
            submitted_by=detail.request.submitted_by,
            submitted_at=detail.request.submitted_at,
        )
    return body


async def _get_task_detail(request: Request) -> JSONResponse:
    task_id = request.path_params["task_id"]
    service: TaskOperatorService = request.app.state.service
    try:
        detail = service.get_detail(task_id)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)

    if detail is None:
        return JSONResponse({"error": f"task {task_id} not found"}, status_code=404)
    return JSONResponse(_detail_to_json(detail))


async def _cancel_task(request: Request) -> JSONResponse:
    task_id = request.path_params["task_id"]
    body_bytes = await request.body()
    reason = _DEFAULT_CANCEL_REASON
    if body_bytes:
        with contextlib.suppress(Exception):
            # A malformed cancel body just falls back to the default reason.
            body = await request.json()
            if isinstance(body, dict) and body.get("reason"):
                reason = str(body["reason"])

    service: TaskOperatorService = request.app.state.service
    try:
        updated = service.cancel(task_id, actor=_DEFAULT_SUBMITTED_BY, reason=reason)
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)

    return JSONResponse(_task_to_json(updated))


async def _health(request: Request) -> JSONResponse:
    service: TaskOperatorService = request.app.state.service
    try:
        service.reader.get_task("__phase3a_health_check__")
    except Exception:
        return JSONResponse({"status": "degraded", "database": "unreachable"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "reachable"})


def _phase3b_service(request: Request) -> Phase3BLifecycleService:
    service: TaskOperatorService = request.app.state.service
    if service.phase3b is None:
        raise OrchestratorApiError("ORCHESTRATOR_UNAVAILABLE", "Phase 3B is not configured")
    return service.phase3b


async def _phase3b_detail(request: Request) -> JSONResponse:
    try:
        detail = _phase3b_service(request).detail(request.path_params["task_id"])
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)
    evidence = detail.evidence
    manifest = detail.manifest
    promotion = detail.promotion
    return JSONResponse(
        {
            "evidence": None
            if evidence is None
            else {
                "run_id": evidence.run_id,
                "digest": evidence.digest(),
                "passed": evidence.passed,
                "created_at": evidence.created_at,
                "items": [
                    {"kind": item.kind, "detail": item.detail, "passed": item.passed}
                    for item in evidence.items
                ],
            },
            "manifest": None
            if manifest is None
            else {
                "run_id": manifest.run_id,
                "digest": manifest.digest(),
                "branch_ref": manifest.branch_ref,
                "base_sha": manifest.base_sha,
                "created_at": manifest.created_at,
                "files": [
                    {"path": item.path, "content_digest": item.content_digest}
                    for item in manifest.files
                ],
            },
            "promotion": None
            if promotion is None
            else {
                "outcome": promotion.outcome.value,
                "reason": promotion.reason,
                "target_ref": promotion.promoted_branch,
                "commit": promotion.promoted_commit_sha,
                "created_at": promotion.created_at,
            },
        }
    )


async def _request_approval(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    target_ref = body.get("target_ref") if isinstance(body, dict) else None
    if not isinstance(target_ref, str) or not target_ref.strip():
        return _bad_request("target_ref is required")
    actor = str(body.get("actor") or _DEFAULT_SUBMITTED_BY)
    try:
        card = _phase3b_service(request).request_approval(
            request.path_params["task_id"], target_ref=target_ref, actor=actor
        )
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)
    return JSONResponse(
        {
            "approval_id": card.approval_id,
            "task_id": card.task_id,
            "target_ref": card.resource,
            "expires_at": card.expires_at,
            "requires_confirmation": card.requires_separate_confirmation,
        },
        status_code=201,
    )


async def _approve(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    approval_id = body.get("approval_id") if isinstance(body, dict) else None
    operator = body.get("operator") if isinstance(body, dict) else None
    confirmed = body.get("confirmed_destructive") if isinstance(body, dict) else None
    if not isinstance(approval_id, str) or not isinstance(operator, str) or confirmed is not True:
        return _bad_request("approval_id, operator, and explicit confirmation are required")
    try:
        result = _phase3b_service(request).approve(
            approval_id, operator=operator, confirmed_destructive=True
        )
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)
    return JSONResponse({"outcome": result.outcome.value, "state": "COMPLETE"})


async def _reject(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    approval_id = body.get("approval_id") if isinstance(body, dict) else None
    operator = body.get("operator") if isinstance(body, dict) else None
    reason = body.get("reason") if isinstance(body, dict) else None
    valid = all(
        isinstance(value, str) and value.strip() for value in (approval_id, operator, reason)
    )
    if not valid:
        return _bad_request("approval_id, operator, and reason are required")
    try:
        result = _phase3b_service(request).reject(
            cast(str, approval_id), operator=cast(str, operator), reason=cast(str, reason)
        )
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)
    return JSONResponse({"outcome": result.outcome.value, "state": "REJECTED"})


def create_app(*, service: TaskOperatorService) -> Starlette:
    """Narrow application factory: the operator service (which holds the writer) is the only
    dependency, passed explicitly. No connection is opened at import time."""
    app = Starlette(
        routes=[
            Route("/api/orchestrator/tasks", _submit_task, methods=["POST"]),
            Route("/api/orchestrator/tasks/{task_id}", _get_task_detail, methods=["GET"]),
            Route("/api/orchestrator/tasks/{task_id}/cancel", _cancel_task, methods=["POST"]),
            Route("/api/orchestrator/tasks/{task_id}/phase3b", _phase3b_detail, methods=["GET"]),
            Route(
                "/api/orchestrator/tasks/{task_id}/approval-requests",
                _request_approval,
                methods=["POST"],
            ),
            Route("/api/orchestrator/tasks/{task_id}/approve", _approve, methods=["POST"]),
            Route("/api/orchestrator/tasks/{task_id}/reject", _reject, methods=["POST"]),
            Route("/api/orchestrator/health", _health, methods=["GET"]),
        ],
    )
    app.state.service = service
    return app
