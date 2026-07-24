"""Task 2.4 — fenced expiring leases (CMP-LEASE)."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.leases.fencing import LeaseManager
from factory.orchestrator.models import LeaseResourceType, ProcessEpoch

_RT = LeaseResourceType.TASK
_RID = "TASK-001"


def _manager(db_path: Path, epoch: ProcessEpoch | None = None) -> LeaseManager:
    return LeaseManager(database_path=db_path, process_epoch=epoch or ProcessEpoch.generate())


def test_tokens_strictly_increase_and_persist_across_restart(db_path: Path) -> None:
    m1 = _manager(db_path)
    first = m1.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    # Simulate a restart: a brand-new manager (new epoch) over the same on-disk DB.
    m2 = _manager(db_path)
    second = m2.acquire(_RT, _RID, owner_id="w2", ttl_seconds=60)
    assert second.fencing_token > first.fencing_token  # counter persisted; strictly increasing


def test_superseded_lower_token_is_rejected(db_path: Path) -> None:
    m = _manager(db_path)
    first = m.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    second = m.acquire(_RT, _RID, owner_id="w2", ttl_seconds=60)
    assert m.validate_token(_RT, _RID, second.fencing_token) is True
    assert m.validate_token(_RT, _RID, first.fencing_token) is False  # superseded


def test_prior_epoch_lease_is_invalid_regardless_of_expiry(db_path: Path) -> None:
    epoch_a = ProcessEpoch.generate()
    m_a = _manager(db_path, epoch_a)
    lease = m_a.acquire(_RT, _RID, owner_id="w1", ttl_seconds=3600)  # far-future expiry
    # A restarted process (different epoch) sees the same highest token but must not trust it.
    m_b = _manager(db_path, ProcessEpoch.generate())
    assert m_b.validate_token(_RT, _RID, lease.fencing_token) is False
    # ...while the original epoch still validates its own current token.
    assert m_a.validate_token(_RT, _RID, lease.fencing_token) is True


def test_renew_extends_only_with_current_token(db_path: Path) -> None:
    m = _manager(db_path)
    lease = m.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    renewed = m.renew(lease, ttl_seconds=120)
    assert renewed.fencing_token == lease.fencing_token
    assert renewed.expires_at >= lease.expires_at


def test_renew_with_stale_token_raises(db_path: Path) -> None:
    m = _manager(db_path)
    first = m.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    m.acquire(_RT, _RID, owner_id="w2", ttl_seconds=60)  # supersedes `first`
    with pytest.raises(OrchestratorError, match="superseded/foreign"):
        m.renew(first, ttl_seconds=120)


def test_release_is_idempotent_and_invalidates_token(db_path: Path) -> None:
    m = _manager(db_path)
    lease = m.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    m.release(lease)
    assert m.validate_token(_RT, _RID, lease.fencing_token) is False
    # Releasing again does not error or mint a new token.
    m.release(lease)
    assert m.validate_token(_RT, _RID, lease.fencing_token) is False


def test_validate_token_true_for_fresh_lease(db_path: Path) -> None:
    m = _manager(db_path)
    lease = m.acquire(_RT, _RID, owner_id="w1", ttl_seconds=60)
    assert m.validate_token(_RT, _RID, lease.fencing_token) is True


def test_validate_token_false_for_unknown_resource(db_path: Path) -> None:
    m = _manager(db_path)
    assert m.validate_token(_RT, "NEVER-ACQUIRED", 1) is False
