from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from factory.integrations.agent_zero.models import AgentZeroEventType, ResourceEnvelope, WorkOrder
from factory.integrations.agent_zero.official_client import AgentZeroPoll
from factory.integrations.agent_zero.transport import TransportFailure, TransportTimeout
from factory.worker_engine.agent_zero_process_client import AgentZeroProcessClient


class OfficialClient:
    def __init__(self, polls: list[AgentZeroPoll]) -> None:
        self.polls = polls
        self.submitted = ""
        self.cancelled: list[str] = []

    def probe(self) -> None:
        return None

    def start_async(self, message: str) -> str:
        self.submitted = message
        return "ctx-1"

    def poll(self, context_id: str) -> AgentZeroPoll:
        assert context_id == "ctx-1"
        return self.polls.pop(0)

    def cancel(self, context_id: str) -> bool:
        self.cancelled.append(context_id)
        return True


def _order(*, timeout_s: int = 30) -> WorkOrder:
    return WorkOrder(
        "wo-1",
        "task-1",
        "ws-1",
        "factory/worker/task-1",
        "target: notes.txt\nUpdate notes.txt",
        frozenset({"read_file", "edit_file"}),
        ("notes.txt",),
        ResourceEnvelope(1000, 1024, 1024, timeout_s),
        timeout_s,
        "opaque-route-token",
    )


def test_official_async_result_is_path_checked_before_disposable_workspace_write(
    tmp_path: Path,
) -> None:
    (tmp_path / "notes.txt").write_text("old\n")
    response = json.dumps(
        {"response": "done", "files": [{"path": "notes.txt", "content": "safe\n"}]}
    )
    official = OfficialClient([AgentZeroPoll("ctx-1", False, response)])
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("notes.txt",),
        clock=lambda: 10,
        sleep=lambda _seconds: None,
    )

    context = client.submit(_order())
    events = client.poll_events(context, after_sequence=-1)

    assert json.loads(official.submitted)["work_order"]["task_id"] == "task-1"
    assert json.loads(official.submitted)["workspace_files"] == [
        {"path": "notes.txt", "content": "old\n"}
    ]
    assert (tmp_path / "notes.txt").read_text() == "safe\n"
    assert [event.event_type for event in events] == [
        AgentZeroEventType.STARTED,
        AgentZeroEventType.PATCH_PROPOSED,
        AgentZeroEventType.EVIDENCE_ATTACHED,
        AgentZeroEventType.COMPLETED,
    ]


def test_official_async_result_rejects_escape_without_writing(tmp_path: Path) -> None:
    response = json.dumps(
        {"response": "done", "files": [{"path": "../escape.txt", "content": "bad"}]}
    )
    official = OfficialClient([AgentZeroPoll("ctx-1", False, response)])
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("**",),
        clock=lambda: 10,
        sleep=lambda _seconds: None,
    )

    context = client.submit(_order())

    with pytest.raises(TransportFailure, match="denied"):
        client.poll_events(context, after_sequence=-1)
    assert not (tmp_path.parent / "escape.txt").exists()


def test_official_async_polling_is_bounded_and_actively_cancelled(tmp_path: Path) -> None:
    official = OfficialClient([AgentZeroPoll("ctx-1", True, None)] * 4)
    ticks = iter((0, 0, 2, 4))
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("notes.txt",),
        clock=lambda: next(ticks),
        sleep=lambda _seconds: None,
    )

    context = client.submit(_order(timeout_s=1))

    with pytest.raises(TransportTimeout, match="timed out"):
        client.poll_events(context, after_sequence=-1)
    assert official.cancelled == ["ctx-1"]


def test_official_async_malformed_reply_fails_closed(tmp_path: Path) -> None:
    official = OfficialClient([AgentZeroPoll("ctx-1", False, "not json")])
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("notes.txt",),
        clock=lambda: 10,
        sleep=lambda _seconds: None,
    )
    context = client.submit(_order())

    with pytest.raises(TransportFailure, match="malformed"):
        client.poll_events(context, after_sequence=-1)


def test_cancel_uses_pinned_official_context(tmp_path: Path) -> None:
    official = OfficialClient([])
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("notes.txt",),
    )
    assert client.cancel("ctx-1") is True
    assert official.cancelled == ["ctx-1"]


def test_active_builder_cancellation_terminates_context_and_emits_cancelled(tmp_path: Path) -> None:
    official = OfficialClient([AgentZeroPoll("ctx-1", True, None)])
    client = AgentZeroProcessClient(
        official=official,
        workspace_path=tmp_path,
        allowed_path_globs=("notes.txt",),
        cancel_requested=lambda task_id: task_id == "task-1",
    )

    context = client.submit(_order())
    events = client.poll_events(context, after_sequence=-1)

    assert official.cancelled == ["ctx-1"]
    assert events[-1].event_type is AgentZeroEventType.CANCELLED


def test_file_results_require_an_explicit_write_or_edit_grant(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("old\n")
    response = json.dumps(
        {"response": "done", "files": [{"path": "notes.txt", "content": "changed\n"}]}
    )
    official = OfficialClient([AgentZeroPoll("ctx-1", False, response)])
    client = AgentZeroProcessClient(official, tmp_path, ("notes.txt",), clock=lambda: 10)
    read_only = dataclasses.replace(_order(), granted_tools=frozenset({"read_file", "search"}))

    context = client.submit(read_only)
    with pytest.raises(TransportFailure, match="write/edit tool grant"):
        client.poll_events(context, after_sequence=-1)
    assert (tmp_path / "notes.txt").read_text() == "old\n"


@pytest.mark.parametrize(
    ("client_kwargs", "files", "match"),
    [
        ({"max_file_count": 1}, [("one.txt", "1"), ("two.txt", "2")], "file count"),
        ({"max_file_bytes": 3}, [("one.txt", "four")], "per-file"),
        ({"max_response_bytes": 40}, [("one.txt", "content")], "response byte"),
    ],
)
def test_result_bounds_fail_before_any_workspace_mutation(
    tmp_path: Path,
    client_kwargs: dict[str, int],
    files: list[tuple[str, str]],
    match: str,
) -> None:
    for path, _content in files:
        (tmp_path / path).write_text("old")
    response = json.dumps(
        {
            "response": "done",
            "files": [{"path": path, "content": content} for path, content in files],
        }
    )
    official = OfficialClient([AgentZeroPoll("ctx-1", False, response)])
    client = AgentZeroProcessClient(
        official, tmp_path, ("*.txt",), clock=lambda: 10, **client_kwargs
    )

    context = client.submit(_order())
    with pytest.raises(TransportFailure, match=match):
        client.poll_events(context, after_sequence=-1)
    assert all((tmp_path / path).read_text() == "old" for path, _content in files)


def test_later_invalid_file_leaves_every_earlier_file_unchanged(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("old\n")
    response = json.dumps(
        {
            "response": "done",
            "files": [
                {"path": "notes.txt", "content": "changed\n"},
                {"path": "../escape.txt", "content": "bad"},
            ],
        }
    )
    client = AgentZeroProcessClient(
        OfficialClient([AgentZeroPoll("ctx-1", False, response)]),
        tmp_path,
        ("**",),
        clock=lambda: 10,
    )

    context = client.submit(_order())
    with pytest.raises(TransportFailure, match="denied"):
        client.poll_events(context, after_sequence=-1)
    assert (tmp_path / "notes.txt").read_text() == "old\n"
    assert not (tmp_path.parent / "escape.txt").exists()


def test_staged_application_rolls_back_all_files_when_later_write_fails(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("old notes\n")
    (tmp_path / "other.txt").write_text("old other\n")
    response = json.dumps(
        {
            "response": "done",
            "files": [
                {"path": "notes.txt", "content": "new notes\n"},
                {"path": "other.txt", "content": "new other\n"},
            ],
        }
    )
    calls: list[Path] = []

    def fail_second_apply(source: Path, destination: Path) -> None:
        calls.append(destination)
        if destination.name == "other.txt" and len(calls) == 2:
            raise OSError("injected later write failure")
        os.replace(source, destination)

    client = AgentZeroProcessClient(
        OfficialClient([AgentZeroPoll("ctx-1", False, response)]),
        tmp_path,
        ("*.txt",),
        clock=lambda: 10,
        replace=fail_second_apply,
    )

    context = client.submit(_order())
    with pytest.raises(TransportFailure, match="rolled back"):
        client.poll_events(context, after_sequence=-1)
    assert (tmp_path / "notes.txt").read_text() == "old notes\n"
    assert (tmp_path / "other.txt").read_text() == "old other\n"


def test_cancellation_after_poll_targets_the_active_upstream_context(tmp_path: Path) -> None:
    official = OfficialClient([AgentZeroPoll("ctx-1", True, None)])
    checks = iter((False, True))
    client = AgentZeroProcessClient(
        official,
        tmp_path,
        ("notes.txt",),
        sleep=lambda _seconds: None,
        cancel_requested=lambda task_id: task_id == "task-1" and next(checks),
    )

    context = client.submit(_order())
    events = client.poll_events(context, after_sequence=-1)

    assert context == "ctx-1"
    assert official.cancelled == [context]
    assert events[-1].event_type is AgentZeroEventType.CANCELLED
