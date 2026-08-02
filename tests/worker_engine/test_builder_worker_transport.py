"""Phase 3B: BuilderWorkerTransport must not require a workspace for read-only tasks, and must
never write outside whatever workspace path it was given (never the live repository).
"""

from __future__ import annotations

from pathlib import Path

from factory.integrations.agent_zero.models import (
    AgentZeroEventType,
    ResourceEnvelope,
    WorkOrder,
)
from factory.integrations.agent_zero.policy import AgentZeroModelResult
from factory.integrations.agent_zero.task_mapping import build_work_order
from factory.worker_engine.builder_worker_transport import (
    BuilderWorkerTransport,
    parse_model_output,
    select_target_path,
)
from factory.worker_engine.model_router import FakeModelRouter

_RESOURCES = ResourceEnvelope(cpu_millis=1000, memory_mb=512, disk_mb=512, wall_clock_s=60)


def _work_order(
    *, instructions: str = "Explain what this repository does.",
    allowed_path_globs: tuple[str, ...] = (),
) -> WorkOrder:
    return build_work_order(
        work_order_id="wo-1",
        task_id="t-1",
        workstream_id="ws-1",
        branch_ref="factory/worker/t-1",
        instructions=instructions,
        granted_tools=frozenset({"read_file"}),
        allowed_path_globs=allowed_path_globs,
        resources=_RESOURCES,
        timeout_s=60,
    )


def test_read_only_task_completes_without_a_workspace(tmp_path: Path) -> None:
    """Requirements 1/2: a read-only task completes without any sandbox/worktree/staging path,
    and the transport never receives or needs one."""
    router = FakeModelRouter(
        default=AgentZeroModelResult(
            ok=True, output="analysis result", model_fingerprint="fp", provider_route="fake",
        )
    )
    transport = BuilderWorkerTransport(model_router=router, allowed_path_globs=())
    assert transport.workspace_path is None

    run_id = transport.submit(_work_order())
    events = transport.poll_events(run_id, after_sequence=-1)

    event_types = [e.event_type for e in events]
    assert event_types == [
        AgentZeroEventType.STARTED,
        AgentZeroEventType.PROGRESS,
        AgentZeroEventType.EVIDENCE_ATTACHED,
        AgentZeroEventType.COMPLETED,
    ]
    # No PATCH_PROPOSED anywhere -- a read-only run proposes no file changes at all.
    assert AgentZeroEventType.PATCH_PROPOSED not in event_types
    # Nothing was ever created on disk for this run.
    assert list(tmp_path.iterdir()) == []


def test_read_only_task_never_touches_the_filesystem_even_with_a_tempting_target_line(
    tmp_path: Path,
) -> None:
    """A malicious/careless instructions string containing a `target:` line must not cause any
    write -- DIRECT_READ_ONLY mode never looks at target-path selection at all."""
    router = FakeModelRouter(
        default=AgentZeroModelResult(
            ok=True, output="analysis result", model_fingerprint="fp", provider_route="fake",
        )
    )
    transport = BuilderWorkerTransport(model_router=router, allowed_path_globs=("**",))
    wo = _work_order(instructions=f"target: {tmp_path}/pwned.txt\nDo some research.")
    run_id = transport.submit(wo)
    events = transport.poll_events(run_id, after_sequence=-1)
    assert AgentZeroEventType.PATCH_PROPOSED not in [e.event_type for e in events]
    assert not (tmp_path / "pwned.txt").exists()
    assert list(tmp_path.iterdir()) == []


def test_write_mode_confines_output_to_the_given_workspace_path(tmp_path: Path) -> None:
    """Requirement 7: even with `allowed_path_globs=("**",)` (maximally permissive), a write-mode
    run can only ever write inside the workspace path it was constructed with -- never the live
    repository, since the transport never holds a reference to any live repo path at all."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    router = FakeModelRouter(
        default=AgentZeroModelResult(
            ok=True,
            output="---BEGIN NEW CONTENT---\nHello\n---END NEW CONTENT---",
            model_fingerprint="fp",
            provider_route="fake",
        )
    )
    transport = BuilderWorkerTransport(
        model_router=router, workspace_path=workspace, allowed_path_globs=("**",)
    )
    wo = _work_order(instructions="target: out.txt\nWrite a greeting.", allowed_path_globs=("**",))
    run_id = transport.submit(wo)
    events = transport.poll_events(run_id, after_sequence=-1)
    assert AgentZeroEventType.COMPLETED in [e.event_type for e in events]
    assert (workspace / "out.txt").read_text() == "Hello"
    # Nothing was ever written outside the workspace directory.
    assert list(tmp_path.iterdir()) == [workspace]


def test_write_mode_rejects_a_path_traversal_attempt_out_of_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    router = FakeModelRouter(
        default=AgentZeroModelResult(
            ok=True,
            output="---BEGIN NEW CONTENT---\nHello\n---END NEW CONTENT---",
            model_fingerprint="fp",
            provider_route="fake",
        )
    )
    transport = BuilderWorkerTransport(
        model_router=router, workspace_path=workspace, allowed_path_globs=("**",)
    )
    wo = _work_order(
        instructions="target: ../../etc/pwned.txt\nEscape the workspace.",
        allowed_path_globs=("**",),
    )
    run_id = transport.submit(wo)
    events = transport.poll_events(run_id, after_sequence=-1)
    event_types = [e.event_type for e in events]
    assert AgentZeroEventType.FAILED in event_types
    assert AgentZeroEventType.PATCH_PROPOSED not in event_types
    assert not (tmp_path / "etc" / "pwned.txt").exists()


def test_select_target_path_defaults_to_a_safe_scratch_file() -> None:
    assert select_target_path("no target line here", "t-42") == "task-output/t-42.md"


def test_select_target_path_extracts_an_explicit_target_line() -> None:
    assert select_target_path("target: src/foo.py\ndo the thing", "t-1") == "src/foo.py"


def test_parse_model_output_returns_none_for_malformed_output() -> None:
    assert parse_model_output("no markers here at all") is None


def test_parse_model_output_extracts_content_between_markers() -> None:
    raw = "preamble\n---BEGIN NEW CONTENT---\nline one\nline two\n---END NEW CONTENT---\ntrailer"
    assert parse_model_output(raw) == "line one\nline two"
