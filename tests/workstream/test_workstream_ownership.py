"""PH-6 unit — single-writer ownership leases (``01D §2.5/§3.2``)."""

from __future__ import annotations

import pytest

from factory.workstream import OwnershipRegistry, WorkstreamError

pytestmark = pytest.mark.security


def test_single_write_owner_per_resource() -> None:
    reg = OwnershipRegistry()
    reg.acquire("src/a.py", "W1")
    assert reg.owner("src/a.py") == "W1"
    with pytest.raises(WorkstreamError) as exc:
        reg.acquire("src/a.py", "W2")  # second writer denied
    assert exc.value.code == "OWNERSHIP_CONFLICT"


def test_same_owner_reacquire_is_allowed() -> None:
    reg = OwnershipRegistry()
    reg.acquire("CTR-X", "W1", is_contract=True)
    lease = reg.acquire("CTR-X", "W1", is_contract=True)  # idempotent for the same owner
    assert lease.is_contract
    assert len(reg.leases()) == 1


def test_release_frees_the_resource() -> None:
    reg = OwnershipRegistry()
    reg.acquire("src/a.py", "W1")
    assert reg.release("src/a.py") is True
    assert reg.release("src/a.py") is False
    assert reg.owner("src/a.py") is None
    reg.acquire("src/a.py", "W2")  # now available to another workstream
    assert reg.owner("src/a.py") == "W2"


def test_workstream_error_repr() -> None:
    err = WorkstreamError("X", "y")
    assert "WorkstreamError(code='X'" in repr(err)
    assert str(err) == "X: y"
