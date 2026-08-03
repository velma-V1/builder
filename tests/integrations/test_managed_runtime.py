from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from factory.integrations.migrations import apply_integration_migrations
from factory.integrations.runtime import (
    CommandResult,
    IntegrationName,
    IntegrationRuntime,
    IntegrationState,
    IntegrationStore,
    ManagedServiceSpec,
    RuntimeFailure,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "integrations"


def _store(tmp_path: Path) -> IntegrationStore:
    database = tmp_path / "integrations.db"
    apply_integration_migrations(database, MIGRATIONS)
    return IntegrationStore(database)


class ScriptedRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...], *, timeout_s: int) -> CommandResult:
        self.commands.append(command)
        if not self.results:
            raise AssertionError(f"unexpected command: {command}")
        return self.results.pop(0)


def _spec(name: IntegrationName = IntegrationName.AGENT_ZERO) -> ManagedServiceSpec:
    return ManagedServiceSpec(
        name=name,
        release="v2.7" if name is IntegrationName.AGENT_ZERO else "v2.5.23",
        commit=(
            "87e1e591e1ba2e8b1a19d34e134fcae490c8dded"
            if name is IntegrationName.AGENT_ZERO
            else "e51058e1765ef2f0c83ccb1d08d984bc59d23f10"
        ),
        compose_file=Path(f"deploy/integrations/{name.value}/compose.yaml"),
        port=50080 if name is IntegrationName.AGENT_ZERO else 3000,
        readiness_url=f"http://127.0.0.1:{50080 if name is IntegrationName.AGENT_ZERO else 3000}/",
        timeout_s=30,
        enabled=True,
        build_from_source=True,
        verify_revision=True,
    )


def test_install_start_stop_records_durable_authoritative_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    runner = ScriptedRunner(
        [
            CommandResult(0, "built", ""),
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(0, "started and healthy", ""),
            CommandResult(0, "stopped", ""),
        ]
    )
    runtime = IntegrationRuntime(store=store, runner=runner, clock=lambda: 10)

    installed = runtime.install(_spec(), actor="operator")
    assert installed.state is IntegrationState.STOPPED
    assert "sha256:image" in installed.detail
    assert _spec().commit in installed.detail
    assert runtime.start(_spec(), actor="operator").state is IntegrationState.READY
    assert runtime.stop(_spec(), actor="operator").state is IntegrationState.STOPPED
    assert store.latest(IntegrationName.AGENT_ZERO).state is IntegrationState.STOPPED
    assert all("--remove-orphans" not in command for command in runner.commands)


def test_start_failure_is_durable_and_does_not_affect_other_service(tmp_path: Path) -> None:
    store = _store(tmp_path)
    runner = ScriptedRunner(
        [
            CommandResult(0, "sha256:agent", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(1, "", "agent failed"),
            CommandResult(0, "cleaned", ""),
            CommandResult(0, "sha256:world", ""),
            CommandResult(0, _spec(IntegrationName.WORLDMONITOR).commit, ""),
            CommandResult(0, "started and healthy", ""),
        ]
    )
    runtime = IntegrationRuntime(store=store, runner=runner, clock=lambda: 20)

    with pytest.raises(RuntimeFailure, match="agent failed"):
        runtime.start(_spec(), actor="operator")
    world = runtime.start(_spec(IntegrationName.WORLDMONITOR), actor="operator")

    assert store.latest(IntegrationName.AGENT_ZERO).state is IntegrationState.FAILED
    assert world.state is IntegrationState.READY


def test_start_waits_for_compose_health_before_ready(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        [
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(0, "healthy", ""),
        ]
    )
    runtime = IntegrationRuntime(store=_store(tmp_path), runner=runner, clock=lambda: 21)

    assert runtime.start(_spec(), actor="operator").state is IntegrationState.READY
    assert runner.commands[-1] == _spec().compose("up", "-d", "--wait", "--wait-timeout", "30")


def test_install_builds_source_and_rejects_revision_mismatch(tmp_path: Path) -> None:
    spec = _spec(IntegrationName.WORLDMONITOR)
    runner = ScriptedRunner(
        [
            CommandResult(0, "built", ""),
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, "wrong", ""),
        ]
    )
    runtime = IntegrationRuntime(_store(tmp_path), runner, lambda: 22)
    with pytest.raises(RuntimeFailure, match="revision mismatch"):
        runtime.install(spec, actor="operator")
    assert runner.commands[0] == spec.compose("build", "--pull")
    assert runtime.store.latest(spec.name).state is IntegrationState.FAILED


def test_disabled_service_fails_closed_without_running_compose(tmp_path: Path) -> None:
    spec = dataclasses.replace(_spec(), enabled=False)
    runner = ScriptedRunner([])
    runtime = IntegrationRuntime(_store(tmp_path), runner, lambda: 23)
    with pytest.raises(RuntimeFailure, match="disabled"):
        runtime.start(spec, actor="operator")
    assert runner.commands == []


@pytest.mark.parametrize("action", ["install", "start", "stop", "disable", "remove"])
def test_every_disabled_lifecycle_action_fails_closed(tmp_path: Path, action: str) -> None:
    spec = dataclasses.replace(_spec(), enabled=False)
    runner = ScriptedRunner([])
    runtime = IntegrationRuntime(_store(tmp_path), runner, lambda: 23)

    with pytest.raises(RuntimeFailure, match="disabled"):
        getattr(runtime, action)(spec, actor="operator")

    assert runner.commands == []


def test_failed_start_cleans_up_and_records_cleanup_failure(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        [
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(1, "", "readiness timeout"),
            CommandResult(1, "", "cleanup denied"),
        ]
    )
    runtime = IntegrationRuntime(_store(tmp_path), runner, lambda: 24)
    with pytest.raises(RuntimeFailure, match="cleanup failed"):
        runtime.start(_spec(), actor="operator")
    detail = runtime.store.latest(IntegrationName.AGENT_ZERO).detail
    assert "readiness timeout" in detail and "cleanup denied" in detail
    assert runner.commands[-1] == _spec().compose("down", "--remove-orphans")


def test_failed_start_records_cleanup_command_exception(tmp_path: Path) -> None:
    class CleanupRunner(ScriptedRunner):
        def run(self, command: tuple[str, ...], *, timeout_s: int) -> CommandResult:
            if command[-2:] == ("down", "--remove-orphans"):
                self.commands.append(command)
                raise RuntimeFailure("cleanup timed out")
            return super().run(command, timeout_s=timeout_s)

    runner = CleanupRunner(
        [
            CommandResult(0, "sha256:image", ""),
            CommandResult(0, _spec().commit, ""),
            CommandResult(1, "", "readiness timeout"),
        ]
    )
    runtime = IntegrationRuntime(_store(tmp_path), runner, lambda: 25)

    with pytest.raises(RuntimeFailure, match="cleanup failed: cleanup timed out"):
        runtime.start(_spec(), actor="operator")
    detail = runtime.store.latest(IntegrationName.AGENT_ZERO).detail
    assert "readiness timeout" in detail
    assert "cleanup timed out" in detail


def test_reconcile_marks_missing_ready_container_failed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.append(IntegrationName.AGENT_ZERO, IntegrationState.READY, "ready", 1)
    runner = ScriptedRunner([CommandResult(1, "", "not running")])
    runtime = IntegrationRuntime(store=store, runner=runner, clock=lambda: 30)

    reconciled = runtime.reconcile((_spec(),))

    assert reconciled[0].state is IntegrationState.FAILED
    assert "not running" in reconciled[0].detail


def test_disable_stops_service_but_never_deletes_data(tmp_path: Path) -> None:
    store = _store(tmp_path)
    runner = ScriptedRunner([CommandResult(0, "stopped", "")])
    runtime = IntegrationRuntime(store=store, runner=runner, clock=lambda: 40)

    record = runtime.disable(_spec(), actor="operator")

    assert record.state is IntegrationState.DISABLED
    command = runner.commands[0]
    assert command[-1] == "stop"
    assert "down" not in command
    assert "--volumes" not in command


def test_remove_tears_down_container_but_preserves_named_volumes(tmp_path: Path) -> None:
    runner = ScriptedRunner([CommandResult(0, "removed", "")])
    runtime = IntegrationRuntime(store=_store(tmp_path), runner=runner, clock=lambda: 41)
    record = runtime.remove(_spec(), actor="operator")
    assert record.state is IntegrationState.NOT_INSTALLED
    assert runner.commands == [_spec().compose("down", "--remove-orphans")]
    assert "--volumes" not in runner.commands[0]


def test_logs_are_bounded_and_failure_text_is_preserved(tmp_path: Path) -> None:
    store = _store(tmp_path)
    runner = ScriptedRunner([CommandResult(0, "line1\nline2\nline3", "")])
    runtime = IntegrationRuntime(store=store, runner=runner, clock=lambda: 50)

    assert runtime.logs(_spec(), tail=2) == ("line2", "line3")
    assert "--tail" in runner.commands[0]


def test_task_and_refresh_results_survive_service_restart(tmp_path: Path) -> None:
    database = tmp_path / "integrations.db"
    apply_integration_migrations(database, MIGRATIONS)
    store = IntegrationStore(database)

    store.save_result(
        IntegrationName.AGENT_ZERO,
        "task-1",
        "SUCCEEDED",
        '{"context_id":"ctx-1","response":"done"}',
        60,
    )
    reopened = IntegrationStore(database)

    result = reopened.latest_result(IntegrationName.AGENT_ZERO)
    assert result is not None
    assert result.operation_id == "task-1"
    assert result.status == "SUCCEEDED"
    assert "ctx-1" in result.payload_json
