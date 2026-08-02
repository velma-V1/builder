"""State contract boundaries: XState owns workflows/legal transitions — never authoritative truth.

Only :data:`StateOwner.BACKEND_AUTHORITATIVE` may claim to own durable truth. A frontend-owned
contract (``XSTATE_WORKFLOW``, ``TANSTACK_QUERY_SNAPSHOT``, ``ZUSTAND_PRESENTATION``) is checked
here and denied if it tries to claim that role, and every declared legal transition must reference
states and events the contract itself declares — no transition through an undeclared state/event.
"""

from __future__ import annotations

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import StateContract, StateOwner

#: Contracts tagged with one of these owners describe frontend-local state — never authoritative.
_NON_AUTHORITATIVE_OWNERS = frozenset(
    {
        StateOwner.XSTATE_WORKFLOW,
        StateOwner.TANSTACK_QUERY_SNAPSHOT,
        StateOwner.ZUSTAND_PRESENTATION,
    }
)


def validate_state_contract(contract: StateContract) -> None:
    """Raise if a non-backend contract claims authority, or a transition is internally
    inconsistent."""
    if contract.owner in _NON_AUTHORITATIVE_OWNERS and "authoritative" in contract.name.lower():
        raise UIStudioError(
            UIStudioErrorCode.STATE_OWNER_VIOLATION,
            f"contract {contract.name!r} is owned by {contract.owner.value}, which may not claim "
            "authoritative state",
        )
    declared_states = set(contract.states)
    declared_events = set(contract.events)
    for from_state, event_name, to_state in contract.legal_transitions:
        if from_state not in declared_states or to_state not in declared_states:
            raise UIStudioError(
                UIStudioErrorCode.ILLEGAL_TRANSITION,
                f"transition ({from_state} --{event_name}--> {to_state}) references an "
                "undeclared state",
            )
        if event_name not in declared_events:
            raise UIStudioError(
                UIStudioErrorCode.ILLEGAL_TRANSITION,
                f"transition ({from_state} --{event_name}--> {to_state}) references an "
                "undeclared event",
            )


def is_transition_legal(contract: StateContract, from_state: str, event_name: str) -> str | None:
    """Return the resulting state if ``(from_state, event_name)`` is legal, else ``None``."""
    for f, e, t in contract.legal_transitions:
        if f == from_state and e == event_name:
            return t
    return None


def builder_command_center_workflow() -> StateContract:
    """A representative XState workflow contract: a task lifecycle (legal transitions only)."""
    return StateContract(
        name="task_lifecycle",
        owner=StateOwner.XSTATE_WORKFLOW,
        states=("queued", "running", "verifying", "awaiting_approval", "complete", "failed"),
        events=("start", "finish", "request_approval", "approve", "reject", "fail"),
        legal_transitions=(
            ("queued", "start", "running"),
            ("running", "finish", "verifying"),
            ("running", "fail", "failed"),
            ("verifying", "request_approval", "awaiting_approval"),
            ("verifying", "fail", "failed"),
            ("awaiting_approval", "approve", "complete"),
            ("awaiting_approval", "reject", "failed"),
        ),
    )
