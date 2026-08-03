"""Data contract boundaries: TanStack Query mirrors the backend; Zustand is presentation-only."""

from __future__ import annotations

import pytest

from factory.ui_studio.data_contracts import (
    builder_task_snapshot_contract,
    sidebar_presentation_contract,
    validate_data_contract,
)
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import DataContract, StateOwner


def test_shipped_task_snapshot_contract_is_valid() -> None:
    validate_data_contract(builder_task_snapshot_contract())  # must not raise


def test_shipped_presentation_contract_is_valid() -> None:
    validate_data_contract(sidebar_presentation_contract())  # must not raise


def test_query_contract_with_no_query_key_is_incomplete() -> None:
    contract = DataContract(
        name="bad", owner=StateOwner.TANSTACK_QUERY_SNAPSHOT, query_key=(), stale_after_s=10
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_data_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.DATA_CONTRACT_INCOMPLETE


def test_query_contract_with_non_positive_staleness_is_incomplete() -> None:
    contract = DataContract(
        name="bad", owner=StateOwner.TANSTACK_QUERY_SNAPSHOT, query_key=("x",), stale_after_s=0
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_data_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.DATA_CONTRACT_INCOMPLETE


def test_presentation_contract_smuggling_backend_shaped_field_is_denied() -> None:
    contract = DataContract(
        name="sneaky",
        owner=StateOwner.ZUSTAND_PRESENTATION,
        query_key=(),
        snapshot_shape={"server_state": "string"},
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_data_contract(contract)
    assert excinfo.value.code is UIStudioErrorCode.STATE_OWNER_VIOLATION


def test_presentation_contract_with_ui_only_fields_is_valid() -> None:
    contract = DataContract(
        name="fine",
        owner=StateOwner.ZUSTAND_PRESENTATION,
        query_key=(),
        snapshot_shape={"collapsed": "boolean"},
    )
    validate_data_contract(contract)  # must not raise
