"""PH-5 — fake WSL2+Docker sandbox backend (provision/destroy/reconcile/boundary)."""

from __future__ import annotations

import pytest

from factory.sandbox import (
    FakeWslDockerBackend,
    ResourceLimits,
    SandboxBackend,
    SandboxError,
    SandboxSpec,
    SandboxStatus,
)


def _spec(**over: object) -> SandboxSpec:
    base: dict[str, object] = dict(
        task_id="T1",
        workstream_id="W1",
        image="factory/base",
        image_version="v1",
        resources=ResourceLimits(1000, 2048, 4096, 128, 600),
    )
    base.update(over)
    return SandboxSpec(**base)  # type: ignore[arg-type]


def test_backend_satisfies_protocol() -> None:
    assert isinstance(FakeWslDockerBackend(), SandboxBackend)


def test_provision_clean_spec_records_identity() -> None:
    backend = FakeWslDockerBackend()
    handle = backend.provision(_spec())
    assert handle.status is SandboxStatus.PROVISIONED
    assert handle.identity is not None
    assert handle.identity.uid == 1000
    assert handle.identity.capabilities == ()  # non-root, no added caps
    # Hardened topology posture is recorded on the granted identity.
    assert handle.identity.read_only_rootfs is True
    assert handle.identity.cap_drop_all is True
    assert handle.identity.no_new_privileges is True
    assert handle.identity.dual_homed is False
    assert handle.identity.network_name == "factory-internal"
    assert backend.status(handle.sandbox_id) is SandboxStatus.PROVISIONED


def test_provision_when_backend_unavailable_is_explicit() -> None:
    backend = FakeWslDockerBackend(available=False)
    handle = backend.provision(_spec())
    assert handle.status is SandboxStatus.RUNTIME_UNAVAILABLE
    assert handle.identity is None
    backend.set_available(True)
    assert backend.provision(_spec()).status is SandboxStatus.PROVISIONED


@pytest.mark.security
def test_provision_policy_violation_is_denied() -> None:
    backend = FakeWslDockerBackend()
    with pytest.raises(SandboxError) as exc:
        backend.provision(_spec(privileged=True))
    assert exc.value.code == "SANDBOX_POLICY_DENIED" and exc.value.security


def test_destroy_is_idempotent() -> None:
    backend = FakeWslDockerBackend()
    handle = backend.provision(_spec())
    assert backend.destroy(handle.sandbox_id) is True
    assert backend.destroy(handle.sandbox_id) is False
    assert backend.status(handle.sandbox_id) is SandboxStatus.DESTROYED
    assert backend.status("never-existed") is SandboxStatus.DESTROYED


def test_reconcile_destroys_orphans() -> None:
    backend = FakeWslDockerBackend()
    keep = backend.provision(_spec())
    orphan = backend.provision(_spec(task_id="T2"))
    destroyed = backend.reconcile(frozenset({keep.sandbox_id}))
    assert destroyed == (orphan.sandbox_id,)
    assert backend.status(keep.sandbox_id) is SandboxStatus.PROVISIONED
    assert backend.status(orphan.sandbox_id) is SandboxStatus.DESTROYED


def test_boundary_failure_destroys_and_requires_clearance() -> None:
    backend = FakeWslDockerBackend()
    handle = backend.provision(_spec())
    report = backend.boundary_failure(handle.sandbox_id, "isolation breach")
    assert report.destroyed is True
    assert report.security_clearance_required is True
    assert backend.status(handle.sandbox_id) is SandboxStatus.FAILED


def test_sandbox_error_repr() -> None:
    err = SandboxError("X", "y", security=True)
    assert "SandboxError(code='X'" in repr(err)
    assert str(err) == "X: y"
