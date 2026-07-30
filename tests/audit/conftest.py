"""Shared fixtures for the roadmap PH-3 audit-chain (RPH3-T4) test suite."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest

from factory.audit import (
    AuditEvent,
    AuditValidator,
    AuditWriter,
    RecordKind,
    apply_audit_migrations,
)

EventFactory = Callable[..., AuditEvent]

AUDIT_MIGRATIONS_ROOT = Path(__file__).resolve().parents[2] / "migrations" / "audit"


@pytest.fixture
def audit_migrations_root() -> Path:
    return AUDIT_MIGRATIONS_ROOT


@pytest.fixture
def audit_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "audit.db"
    apply_audit_migrations(path, AUDIT_MIGRATIONS_ROOT)
    return path


@pytest.fixture
def writer(audit_db_path: Path) -> AuditWriter:
    return AuditWriter(database_path=audit_db_path)


@pytest.fixture
def validator(audit_db_path: Path) -> AuditValidator:
    return AuditValidator(database_path=audit_db_path)


def _make_event(
    op_key: str,
    *,
    record_kind: RecordKind = RecordKind.COMPLETION,
    operation_class: int = 1,
    actor: str = "cmp-perm",
    action_class: str = "privileged",
    payload: str = "payload",
    occurred_at: str = "2026-07-26T00:00:00Z",
    target_ref: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        op_key=op_key,
        record_kind=record_kind,
        operation_class=operation_class,
        actor=actor,
        action_class=action_class,
        payload_hash=hashlib.sha256(payload.encode()).hexdigest(),
        occurred_at=occurred_at,
        target_ref=target_ref,
    )


@pytest.fixture
def make_event() -> EventFactory:
    """Factory fixture for building ``AuditEvent`` values in tests."""
    return _make_event
