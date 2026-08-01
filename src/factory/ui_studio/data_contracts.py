"""Data contract boundaries: TanStack Query mirrors backend snapshots; Zustand is presentation-only.

A :class:`DataContract` describes a bounded, backend-sourced cache entry — never a place for a
client to invent a field the backend never sent. ``ZUSTAND_PRESENTATION`` contracts are checked to
ensure they carry no field that reads as backend-authoritative data (e.g. ``server_state``,
``record``, ``snapshot``) — that state belongs in TanStack Query, not local presentation state.
"""

from __future__ import annotations

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import DataContract, StateOwner

#: Substrings that suggest a presentation-only contract is smuggling backend-owned data.
_BACKEND_SHAPED_FIELD_HINTS = ("server_state", "record", "snapshot", "authoritative")


def validate_data_contract(contract: DataContract) -> None:
    if contract.owner is StateOwner.TANSTACK_QUERY_SNAPSHOT:
        if not contract.query_key:
            raise UIStudioError(
                UIStudioErrorCode.DATA_CONTRACT_INCOMPLETE,
                f"data contract {contract.name!r} declares no query_key",
            )
        if contract.stale_after_s <= 0:
            raise UIStudioError(
                UIStudioErrorCode.DATA_CONTRACT_INCOMPLETE,
                f"data contract {contract.name!r} must declare a positive staleness window",
            )
    if contract.owner is StateOwner.ZUSTAND_PRESENTATION:
        if contract.query_key:
            raise UIStudioError(
                UIStudioErrorCode.STATE_OWNER_VIOLATION,
                f"presentation-only contract {contract.name!r} declares a query_key "
                f"{contract.query_key!r}; a backend query belongs in a TANSTACK_QUERY_SNAPSHOT "
                "contract, not presentation state",
            )
        hit = next(
            (
                field for field in contract.snapshot_shape
                if any(h in field.lower() for h in _BACKEND_SHAPED_FIELD_HINTS)
            ),
            None,
        )
        if hit is not None:
            raise UIStudioError(
                UIStudioErrorCode.STATE_OWNER_VIOLATION,
                f"presentation-only contract {contract.name!r} declares backend-shaped field "
                f"{hit!r}; backend-sourced data belongs in a TANSTACK_QUERY_SNAPSHOT contract",
            )


def builder_task_snapshot_contract() -> DataContract:
    return DataContract(
        name="task_snapshot",
        owner=StateOwner.TANSTACK_QUERY_SNAPSHOT,
        query_key=("tasks", "byWorkstream"),
        snapshot_shape={"task_id": "string", "state": "string", "updated_at": "number"},
        stale_after_s=15,
    )


def sidebar_presentation_contract() -> DataContract:
    return DataContract(
        name="sidebar_ui_state",
        owner=StateOwner.ZUSTAND_PRESENTATION,
        query_key=(),
        snapshot_shape={"collapsed": "boolean", "active_tab": "string"},
        stale_after_s=0,
    )
