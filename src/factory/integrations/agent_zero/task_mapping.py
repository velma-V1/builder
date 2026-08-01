"""Build a :class:`WorkOrder` — the entire grant Agent Zero receives for one unit of work.

The only place a ``WorkOrder`` is constructed. Every construction is checked against the authority
Agent Zero must never hold (direct ``main`` access, a smuggled scheduling hint) before it exists,
not after — a caller cannot accidentally hand out a forbidden grant.
"""

from __future__ import annotations

from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.models import ResourceEnvelope, WorkOrder
from factory.integrations.agent_zero.policy import deny_direct_main_access, deny_hidden_scheduling


def build_work_order(
    *,
    work_order_id: str,
    task_id: str,
    workstream_id: str,
    branch_ref: str,
    instructions: str,
    granted_tools: frozenset[str],
    allowed_path_globs: tuple[str, ...],
    resources: ResourceEnvelope,
    timeout_s: int,
    model_route_token: str = "",
) -> WorkOrder:
    """Map a Builder-side assignment into a :class:`WorkOrder`. Denies before it ever exists."""
    deny_direct_main_access(branch_ref)
    if timeout_s <= 0:
        raise AgentZeroError(
            AgentZeroErrorCode.CAPABILITY_UNAVAILABLE, "timeout_s must be positive"
        )
    if not granted_tools:
        raise AgentZeroError(
            AgentZeroErrorCode.TOOL_DENIED, "a work order must explicitly grant at least one tool"
        )
    order = WorkOrder(
        work_order_id=work_order_id,
        task_id=task_id,
        workstream_id=workstream_id,
        branch_ref=branch_ref,
        instructions=instructions,
        granted_tools=granted_tools,
        allowed_path_globs=allowed_path_globs,
        resources=resources,
        timeout_s=timeout_s,
        model_route_token=model_route_token,
    )
    deny_hidden_scheduling(order)
    return order
