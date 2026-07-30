"""Models for the roadmap PH-3 tamper-evident audit chain (CMP-AUDITW / CMP-AUDITV).

The audit chain is a separate, append-only, hash-chained store (DEP-RPH3 §2/§3; not the frozen
runtime-state DB). An operation identified by ``op_key`` may carry up to two lifecycle records:
one ``INTENT`` (Class-3 pre-execution) and one ``COMPLETION`` (post-execution, or the sole record
of a Class-1/2 operation). Chain identity fields (``sequence``, ``predecessor_hash``,
``record_hash``) are computed by the writer, never accepted from the caller (forge-resistance).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

# Genesis predecessor for the first record in a chain (64 hex zeros).
GENESIS_ANCHOR = "0" * 64

# Field separator for the canonical hashed serialization (ASCII unit separator: not valid in the
# hex/identifier fields it joins, so the concatenation is unambiguous).
_SEP = "\x1f"


class RecordKind(StrEnum):
    INTENT = "INTENT"
    COMPLETION = "COMPLETION"


class BreakClass(StrEnum):
    DELETION = "deletion"
    TRUNCATION = "truncation"
    REORDER = "reorder"
    REWRITE = "rewrite"
    BAD_ANCHOR = "bad_anchor"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Untrusted input to ``AuditWriter.append``. Carries no chain-identity fields.

    ``payload_hash`` is the SHA-256 of any untrusted payload the caller wants referenced; the raw
    payload is never stored here or executed (01K §3.2 / Zone-3 untrusted). ``operation_class`` is
    the XSC-RPH3 class (1/2/3); a Class-3 ``COMPLETION`` requires a prior ``INTENT`` for ``op_key``.
    """

    op_key: str
    record_kind: RecordKind
    operation_class: int
    actor: str
    action_class: str
    payload_hash: str
    occurred_at: str
    target_ref: str | None = None


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """A durable, hash-chained audit record as stored/returned by the writer."""

    record_id: int
    sequence: int
    op_key: str
    record_kind: RecordKind
    operation_class: int
    actor: str
    action_class: str
    target_ref: str | None
    payload_hash: str
    occurred_at: str
    predecessor_hash: str
    record_hash: str
    signature: str | None = None

    @staticmethod
    def compute_hash(
        *,
        sequence: int,
        op_key: str,
        record_kind: RecordKind,
        operation_class: int,
        actor: str,
        action_class: str,
        target_ref: str | None,
        payload_hash: str,
        occurred_at: str,
        predecessor_hash: str,
    ) -> str:
        """Deterministic content+position hash. Binds the record to its chain slot."""
        canonical = _SEP.join(
            (
                str(sequence),
                op_key,
                str(record_kind),
                str(operation_class),
                actor,
                action_class,
                target_ref or "",
                payload_hash,
                occurred_at,
                predecessor_hash,
            )
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def recompute_hash(self) -> str:
        return AuditRecord.compute_hash(
            sequence=self.sequence,
            op_key=self.op_key,
            record_kind=self.record_kind,
            operation_class=self.operation_class,
            actor=self.actor,
            action_class=self.action_class,
            target_ref=self.target_ref,
            payload_hash=self.payload_hash,
            occurred_at=self.occurred_at,
            predecessor_hash=self.predecessor_hash,
        )


@dataclass(frozen=True, slots=True)
class ChainHead:
    """A reference to a chain tip, used to detect tail truncation across a later verification."""

    sequence: int
    record_hash: str


@dataclass(frozen=True, slots=True)
class IntegrityVerdict:
    """Result of a chain verification. ``valid`` iff no break was detected."""

    valid: bool
    break_class: BreakClass | None = None
    first_bad_sequence: int | None = None
    detail: str | None = None
