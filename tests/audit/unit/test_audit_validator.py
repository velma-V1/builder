"""RPH3-T4 unit — audit validator: a well-formed chain verifies clean."""

from __future__ import annotations

from collections.abc import Callable

from factory.audit import (
    AuditEvent,
    AuditValidator,
    AuditWriter,
    BreakClass,
    ChainHead,
    RecordKind,
)

EventFactory = Callable[..., AuditEvent]


def test_empty_chain_is_valid(validator: AuditValidator) -> None:
    verdict = validator.verify_chain()
    assert verdict.valid is True


def test_empty_chain_with_expected_head_is_truncation(validator: AuditValidator) -> None:
    verdict = validator.verify_chain(expected_head=ChainHead(sequence=1, record_hash="abc"))
    assert verdict.valid is False
    assert AuditValidator.classify_break(verdict) is BreakClass.TRUNCATION


def test_well_formed_chain_verifies(
    writer: AuditWriter, validator: AuditValidator, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1"))
    writer.append(make_event("op-c3", record_kind=RecordKind.INTENT, operation_class=3))
    writer.append(make_event("op-c3", record_kind=RecordKind.COMPLETION, operation_class=3))
    writer.append(make_event("op-2"))
    verdict = validator.verify_chain()
    assert verdict.valid is True
    assert verdict.break_class is None


def test_verify_export_matches_chain(
    writer: AuditWriter, validator: AuditValidator, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1"))
    writer.append(make_event("op-2"))
    exported = writer.export()
    assert validator.verify_export(exported).valid is True


def test_expected_head_matches(
    writer: AuditWriter, validator: AuditValidator, make_event: EventFactory
) -> None:
    writer.append(make_event("op-1"))
    writer.append(make_event("op-2"))
    head = writer.chain_head()
    assert head is not None
    assert validator.verify_chain(expected_head=head).valid is True
