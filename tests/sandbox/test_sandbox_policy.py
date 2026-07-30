"""PH-5 unit — sandbox isolation policy (``01E §3.1/§3.2``, Decision C)."""

from __future__ import annotations

import pytest

from factory.sandbox import (
    MountMode,
    MountSpec,
    ResourceLimits,
    SandboxSpec,
    evaluate_spec,
)


def _spec(**over: object) -> SandboxSpec:
    base: dict[str, object] = dict(
        task_id="T1",
        workstream_id="W1",
        image="factory/base",
        image_version="v1",
        resources=ResourceLimits(
            cpu_millis=1000, memory_mb=2048, disk_mb=4096, pids=128, wall_clock_s=600
        ),
    )
    base.update(over)
    return SandboxSpec(**base)  # type: ignore[arg-type]


def test_clean_spec_has_no_violations() -> None:
    assert evaluate_spec(_spec()) == ()


@pytest.mark.security
@pytest.mark.parametrize(
    ("flag", "code"),
    [
        ("windows_native", "WINDOWS_NATIVE_DENIED"),
        ("privileged", "PRIVILEGED_DENIED"),
        ("host_docker_socket", "HOST_SOCKET_DENIED"),
        ("host_pid_namespace", "HOST_PID_NS_DENIED"),
        ("host_ipc_namespace", "HOST_IPC_NS_DENIED"),
        ("host_network", "HOST_NET_DENIED"),
    ],
)
def test_prohibited_flags_are_denied(flag: str, code: str) -> None:
    codes = {v.code for v in evaluate_spec(_spec(**{flag: True}))}
    assert code in codes


@pytest.mark.security
def test_root_execution_denied_two_ways() -> None:
    assert any(v.code == "ROOT_DENIED" for v in evaluate_spec(_spec(run_as_root=True)))
    assert any(v.code == "ROOT_DENIED" for v in evaluate_spec(_spec(uid=0)))


@pytest.mark.security
def test_writable_host_project_mount_denied() -> None:
    mount = MountSpec("/host/proj", "/work", MountMode.RW, is_host_project=True)
    codes = {v.code for v in evaluate_spec(_spec(mounts=(mount,)))}
    assert "HOST_PROJECT_WRITE_DENIED" in codes


def test_readonly_host_project_mount_allowed() -> None:
    mount = MountSpec("/host/proj", "/work", MountMode.RO, is_host_project=True)
    assert evaluate_spec(_spec(mounts=(mount,))) == ()


def test_nonpositive_resource_limits_denied() -> None:
    bad = ResourceLimits(cpu_millis=1000, memory_mb=0, disk_mb=4096, pids=128, wall_clock_s=600)
    codes = {v.code for v in evaluate_spec(_spec(resources=bad))}
    assert "RESOURCE_LIMITS_REQUIRED" in codes
