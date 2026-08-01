"""State contract boundaries: XState owns legal transitions, never authoritative truth."""

from __future__ import annotations

import pytest

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import StateContract, StateOwner
from factory.ui_studio.state_contracts import (
    builder_command_center_workflow,
    is_transition_legal,
    validate_state_contract,
)


def test_shipped_workflow_contract_is_valid() -> None:
    validate_state_contract(builder_command_center_workflow())  # must not raise


def test_legal_transition_resolves_target_state() -> None:
    contract = builder_command_center_workflow()
    assert is_transition_legal(contract, "queued", "start") == "running"


def test_illegal_transition_returns_none() -> None:
    contract = builder_command_center_workflow()
    assert is_transition_legal(contract, "queued", "approve") is None


def test_transition_referencing_undeclared_state_is_denied() -> None:
    contract = StateContract(
        name="bad", owner=StateOwner.XSTATE_WORKFLOW, states=("a", "b"), events=("go",),
        legal_transitions=(("a", "go", "c"),),  # "c" was never declared
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_state_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.ILLEGAL_TRANSITION


def test_transition_referencing_undeclared_event_is_denied() -> None:
    contract = StateContract(
        name="bad", owner=StateOwner.XSTATE_WORKFLOW, states=("a", "b"), events=("go",),
        legal_transitions=(("a", "ghost_event", "b"),),
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_state_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.ILLEGAL_TRANSITION


def test_frontend_owned_contract_cannot_claim_to_be_authoritative() -> None:
    contract = StateContract(
        name="authoritative_task_state",  # name itself claims authority
        owner=StateOwner.XSTATE_WORKFLOW, states=("a",), events=(), legal_transitions=(),
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_state_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.STATE_OWNER_VIOLATION


def test_backend_authoritative_contract_may_use_the_authoritative_name() -> None:
    contract = StateContract(
        name="authoritative_task_state", owner=StateOwner.BACKEND_AUTHORITATIVE,
        states=("a",), events=(), legal_transitions=(),
    )
    validate_state_contract(contract)  # must not raise
