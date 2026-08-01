"""Phase 2B — TaskRuntimeRecord -> TaskSnapshot mapping.

Mirrors factory.ui_studio.data_contracts.builder_task_snapshot_contract() and
ui/src/queries/useTaskSnapshot.ts exactly: {task_id, state, updated_at}, with
updated_at as a UTC Unix epoch integer in milliseconds.
"""

from __future__ import annotations

from factory.api.mapping import to_task_snapshot
from factory.orchestrator.models import TaskRuntimeRecord, TaskState


def _record(**overrides: object) -> TaskRuntimeRecord:
    defaults: dict[str, object] = {
        "task_id": "TASK-001",
        "project_id": "PROJ-001",
        "contract_version": 1,
        "current_state": TaskState.RUNNING,
        "sequence": 3,
        "updated_at": "2026-01-01T00:00:00Z",
        "workstream_id": "ws-1",
    }
    defaults.update(overrides)
    return TaskRuntimeRecord(**defaults)  # type: ignore[arg-type]


def test_mapping_produces_exactly_the_three_contract_keys() -> None:
    snapshot = to_task_snapshot(_record())
    assert set(snapshot.keys()) == {"task_id", "state", "updated_at"}


def test_state_uses_the_enum_string_value_not_the_python_repr() -> None:
    snapshot = to_task_snapshot(_record(current_state=TaskState.AWAITING_APPROVAL))
    assert snapshot["state"] == "AWAITING_APPROVAL"
    assert isinstance(snapshot["state"], str)


def test_task_id_passes_through_unchanged() -> None:
    snapshot = to_task_snapshot(_record(task_id="TASK-XYZ"))
    assert snapshot["task_id"] == "TASK-XYZ"


def test_updated_at_epoch_start_converts_to_zero_milliseconds() -> None:
    snapshot = to_task_snapshot(_record(updated_at="1970-01-01T00:00:00Z"))
    assert snapshot["updated_at"] == 0
    assert isinstance(snapshot["updated_at"], int)


def test_updated_at_known_instant_converts_to_exact_epoch_milliseconds() -> None:
    # 2026-01-01T00:00:00Z is a known, hand-verifiable instant.
    snapshot = to_task_snapshot(_record(updated_at="2026-01-01T00:00:00Z"))
    assert snapshot["updated_at"] == 1_767_225_600_000


def test_updated_at_one_second_later_differs_by_exactly_1000_ms() -> None:
    earlier = to_task_snapshot(_record(updated_at="2026-06-15T12:00:00Z"))
    later = to_task_snapshot(_record(updated_at="2026-06-15T12:00:01Z"))
    assert later["updated_at"] - earlier["updated_at"] == 1000


def test_mapping_leaks_no_internal_fields() -> None:
    snapshot = to_task_snapshot(_record())
    for internal_field in ("project_id", "contract_version", "sequence", "workstream_id"):
        assert internal_field not in snapshot
