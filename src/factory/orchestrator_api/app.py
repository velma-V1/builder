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
import json
from typing import Any, cast

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from factory.integrations.control import IntegrationControlService
from factory.integrations.model_gateway import ModelGateway, ModelGatewayError
from factory.integrations.runtime import IntegrationName, IntegrationOperation, IntegrationRecord
from factory.integrations.worldmonitor.manifest import WORLDMONITOR_MANIFEST
from factory.orchestrator.models import TaskRuntimeRecord
from factory.orchestrator_api.auth import OperatorSession
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


def _authenticated_operator(request: Request) -> str | JSONResponse:
    session: OperatorSession | None = request.app.state.operator_session
    if session is None:
        return JSONResponse({"error": "operator session unavailable"}, status_code=503)
    operator = session.authenticate(request.headers.get("authorization"))
    if operator is None:
        return JSONResponse({"error": "operator authentication required"}, status_code=401)
    return operator


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
    approval = detail.approval
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
            "approval": None
            if approval is None
            else {
                "approval_id": approval.approval_id,
                "state": approval.state.value,
                "target_ref": approval.resource,
                "expires_at": approval.expires_at,
                "requires_confirmation": approval.requires_confirmation,
            },
        }
    )


async def _request_approval(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    target_ref = body.get("target_ref") if isinstance(body, dict) else None
    if not isinstance(target_ref, str) or not target_ref.strip():
        return _bad_request("target_ref is required")
    try:
        card = _phase3b_service(request).request_approval(
            request.path_params["task_id"], target_ref=target_ref, actor=operator
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
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    approval_id = body.get("approval_id") if isinstance(body, dict) else None
    confirmed = body.get("confirmed_destructive") if isinstance(body, dict) else None
    if not isinstance(approval_id, str) or confirmed is not True:
        return _bad_request("approval_id and explicit confirmation are required")
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
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    approval_id = body.get("approval_id") if isinstance(body, dict) else None
    reason = body.get("reason") if isinstance(body, dict) else None
    valid = all(isinstance(value, str) and value.strip() for value in (approval_id, reason))
    if not valid:
        return _bad_request("approval_id and reason are required")
    try:
        result = _phase3b_service(request).reject(
            cast(str, approval_id), operator=operator, reason=cast(str, reason)
        )
    except OrchestratorApiError as exc:
        return _error_response(exc)
    except Exception:
        return JSONResponse({"error": "orchestrator temporarily unavailable"}, status_code=503)
    return JSONResponse({"outcome": result.outcome.value, "state": "REJECTED"})


def _integration_service(request: Request) -> IntegrationControlService | JSONResponse:
    service: IntegrationControlService | None = request.app.state.integration_control
    if service is None:
        return JSONResponse({"error": "managed integrations are unavailable"}, status_code=503)
    return service


def _integration_record(record: IntegrationRecord) -> dict[str, object]:
    return {
        "name": record.name.value,
        "state": record.state.value,
        "detail": record.detail,
        "occurred_at": record.occurred_at,
    }


def _integration_result(record: IntegrationOperation) -> dict[str, object]:
    return {
        "operation_id": record.operation_id,
        "status": record.state.value,
        "occurred_at": record.updated_at,
        "context_id": record.context_id,
        "reason": record.reason,
        "payload": json.loads(record.result_json) if record.result_json else {},
    }


def _integration_name(raw: str) -> IntegrationName | None:
    with contextlib.suppress(ValueError):
        return IntegrationName(raw)
    return None


def _disabled_response(
    service: IntegrationControlService, name: IntegrationName
) -> JSONResponse | None:
    if not service.is_enabled(name):
        return JSONResponse(
            {"error": f"{name.value} is disabled in Builder configuration"}, status_code=409
        )
    return None


async def _integration_status(request: Request) -> JSONResponse:
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    statuses: dict[str, object] = {}
    for name in (IntegrationName.AGENT_ZERO, IntegrationName.WORLDMONITOR):
        status = _integration_record(service.status(name))
        status["configured_enabled"] = service.is_enabled(name)
        if name is IntegrationName.WORLDMONITOR:
            status["capability_coverage"] = {
                "status": "INCOMPLETE",
                "implemented": list(WORLDMONITOR_MANIFEST.implemented_capability_scope),
                "required": list(WORLDMONITOR_MANIFEST.approved_capability_scope),
            }
        operation = service.latest_operation(name)
        status["operation"] = None if operation is None else _integration_result(operation)
        statuses[name.value] = status
    return JSONResponse(statuses)


async def _model_completion(request: Request) -> JSONResponse:
    gateway: ModelGateway | None = request.app.state.model_gateway
    if gateway is None:
        return JSONResponse({"error": "model gateway unavailable"}, status_code=503)
    try:
        payload = await request.json()
        result = gateway.complete(request.headers.get("Authorization", ""), payload)
    except ModelGatewayError as exc:
        status = 401 if "authentication" in str(exc) else 503
        return JSONResponse({"error": str(exc)}, status_code=status)
    except Exception:
        return _bad_request("model request must be valid JSON")
    return JSONResponse(result)


async def _integration_action(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    name = _integration_name(request.path_params["name"])
    action = request.path_params["action"]
    if name is None or action not in {"install", "start", "stop", "disable", "remove"}:
        return JSONResponse({"error": "unknown integration action"}, status_code=404)
    if (disabled := _disabled_response(service, name)) is not None:
        return disabled
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    operation_id = body.get("operation_id") if isinstance(body, dict) else None
    if not isinstance(operation_id, str) or not operation_id.strip():
        return _bad_request("operation_id is required")
    try:
        method = getattr(service, action)
        record = method(name, actor=operator, operation_id=operation_id)
    except Exception:
        return JSONResponse({"error": "integration action failed"}, status_code=503)
    return JSONResponse(_integration_record(record))


async def _integration_logs(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    name = _integration_name(request.path_params["name"])
    if name is None:
        return JSONResponse({"error": "unknown integration"}, status_code=404)
    if (disabled := _disabled_response(service, name)) is not None:
        return disabled
    try:
        tail = int(request.query_params.get("tail", "200"))
        lines = service.logs(name, tail=tail)
    except (ValueError, RuntimeError):
        return _bad_request("tail must be between 1 and 1000")
    return JSONResponse({"lines": list(lines)})


async def _agent_cancel(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    if (disabled := _disabled_response(service, IntegrationName.AGENT_ZERO)) is not None:
        return disabled
    try:
        body = await request.json()
        operation_id = body["operation_id"]
    except (KeyError, TypeError):
        return _bad_request("operation_id is required")
    if not isinstance(operation_id, str) or not operation_id.strip():
        return _bad_request("operation_id is required")
    try:
        task_service: TaskOperatorService = request.app.state.service
        operation = service.cancel_agent_task(
            operation_id,
            lambda task_id: task_service.cancel(
                task_id, actor=operator, reason="Agent Zero operation cancelled"
            ),
        )
    except Exception:
        return JSONResponse({"error": "Agent Zero cancellation failed"}, status_code=503)
    return JSONResponse(_integration_result(operation))


async def _agent_task(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    if (disabled := _disabled_response(service, IntegrationName.AGENT_ZERO)) is not None:
        return disabled
    try:
        body = await request.json()
    except Exception:
        return _bad_request("request body must be valid JSON")
    operation_id = body.get("operation_id") if isinstance(body, dict) else None
    instructions = body.get("instructions") if isinstance(body, dict) else None
    valid = all(isinstance(value, str) and value.strip() for value in (operation_id, instructions))
    if not valid:
        return _bad_request("operation_id and instructions are required")
    try:
        task_service: TaskOperatorService = request.app.state.service
        request_json = json.dumps(
            {"instructions": instructions}, sort_keys=True, separators=(",", ":")
        )

        def submit() -> str:
            submitted = task_service.submit(
                project_ref="builder",
                workstream_id="agent-zero",
                description=cast(str, instructions),
                priority="normal",
                model_preference="agent-zero",
                expected_result="independently verified Builder work product",
                submitted_by=operator,
                idempotency_key=f"agent-zero:{cast(str, operation_id)}",
            )
            return submitted.task_id

        result = service.dispatch_agent_task(
            cast(str, operation_id), request_json, actor=operator, submit=submit
        )
    except Exception:
        return JSONResponse({"error": "Agent Zero task failed"}, status_code=503)
    return JSONResponse(_integration_result(result))


async def _agent_operation(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    if (disabled := _disabled_response(service, IntegrationName.AGENT_ZERO)) is not None:
        return disabled
    try:
        task_service: TaskOperatorService = request.app.state.service
        operation = service.reconcile_agent_task(
            request.path_params["operation_id"],
            lambda task_id: (
                detail.task.current_state if (detail := task_service.get_detail(task_id)) else None
            ),
        )
    except Exception:
        return JSONResponse({"error": "Agent Zero operation unavailable"}, status_code=404)
    return JSONResponse(_integration_result(operation))


async def _worldmonitor_refresh(request: Request) -> JSONResponse:
    operator = _authenticated_operator(request)
    if isinstance(operator, JSONResponse):
        return operator
    service = _integration_service(request)
    if isinstance(service, JSONResponse):
        return service
    if (disabled := _disabled_response(service, IntegrationName.WORLDMONITOR)) is not None:
        return disabled
    try:
        body = await request.json()
        operation_id = body["operation_id"]
        start_ms = int(body["start_ms"])
        end_ms = int(body["end_ms"])
        limit = int(body.get("limit", 50))
    except (KeyError, TypeError, ValueError):
        return _bad_request("operation_id, start_ms, end_ms, and a valid limit are required")
    if not isinstance(operation_id, str) or not operation_id.strip():
        return _bad_request("operation_id is required")
    try:
        result = service.refresh_worldmonitor(
            operation_id,
            start_ms=start_ms,
            end_ms=end_ms,
            limit=limit,
            actor=operator,
        )
    except Exception:
        return JSONResponse({"error": "WorldMonitor refresh failed"}, status_code=503)
    return JSONResponse(_integration_result(result))


def create_app(
    *,
    service: TaskOperatorService,
    operator_session: OperatorSession | None = None,
    integration_control: IntegrationControlService | None = None,
    model_gateway: ModelGateway | None = None,
) -> Starlette:
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
            Route("/api/orchestrator/integrations", _integration_status, methods=["GET"]),
            Route(
                "/api/integrations/model/v1/chat/completions",
                _model_completion,
                methods=["POST"],
            ),
            Route(
                "/api/orchestrator/integrations/agent-zero/tasks",
                _agent_task,
                methods=["POST"],
            ),
            Route(
                "/api/orchestrator/integrations/agent-zero/cancel",
                _agent_cancel,
                methods=["POST"],
            ),
            Route(
                "/api/orchestrator/integrations/agent-zero/tasks/{operation_id}",
                _agent_operation,
                methods=["GET"],
            ),
            Route(
                "/api/orchestrator/integrations/{name}/logs",
                _integration_logs,
                methods=["GET"],
            ),
            Route(
                "/api/orchestrator/integrations/worldmonitor/refresh",
                _worldmonitor_refresh,
                methods=["POST"],
            ),
            Route(
                "/api/orchestrator/integrations/{name}/{action}",
                _integration_action,
                methods=["POST"],
            ),
        ],
    )
    app.state.service = service
    app.state.operator_session = operator_session
    app.state.integration_control = integration_control
    app.state.model_gateway = model_gateway
    return app
