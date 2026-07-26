"""Audit-chain integrity validator (roadmap PH-3, CMP-AUDITV).

Read-only over CMP-AUDITW's store. Recomputes the hash chain and detects deletion, truncation,
reordering, rewriting, and an invalid genesis anchor, then classifies the first break. It never
writes or repairs; while a break is unresolved, audit records are non-authoritative
(01K-AC-20 / audit-validator-spec). Local records are not claimed absolutely immutable against the
machine owner — this provides tamper-EVIDENCE (01K §3.2): even a tamper performed by dropping the
append-only triggers and editing rows directly is detected here.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.audit.models import (
    GENESIS_ANCHOR,
    AuditRecord,
    BreakClass,
    ChainHead,
    IntegrityVerdict,
    RecordKind,
)
from factory.contracts.activation.store import _reader_authorizer

# Fully-literal SQL (no interpolation) — read-only + no static-analysis exception needed.
_SELECT_PHYSICAL_SQL = (
    "SELECT record_id, sequence, op_key, record_kind, operation_class, actor, action_class, "
    "target_ref, payload_hash, occurred_at, predecessor_hash, record_hash, signature "
    "FROM audit_records ORDER BY record_id"
)


def _row_to_record(row: sqlite3.Row) -> AuditRecord:
    return AuditRecord(
        record_id=int(row["record_id"]),
        sequence=int(row["sequence"]),
        op_key=row["op_key"],
        record_kind=RecordKind(row["record_kind"]),
        operation_class=int(row["operation_class"]),
        actor=row["actor"],
        action_class=row["action_class"],
        target_ref=row["target_ref"],
        payload_hash=row["payload_hash"],
        occurred_at=row["occurred_at"],
        predecessor_hash=row["predecessor_hash"],
        record_hash=row["record_hash"],
        signature=row["signature"],
    )


def _valid() -> IntegrityVerdict:
    return IntegrityVerdict(valid=True)


def _broken(break_class: BreakClass, sequence: int | None, detail: str) -> IntegrityVerdict:
    return IntegrityVerdict(
        valid=False, break_class=break_class, first_bad_sequence=sequence, detail=detail
    )


@dataclass(frozen=True, slots=True)
class AuditValidator:
    """Read-only integrity verifier for the audit chain."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        return connection

    def _read_physical(self) -> tuple[AuditRecord, ...]:
        """Records in physical insertion order (``record_id``) so a physical reorder is visible."""
        connection = self._connect()
        try:
            rows = connection.execute(_SELECT_PHYSICAL_SQL).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_record(r) for r in rows)

    def verify_chain(self, *, expected_head: ChainHead | None = None) -> IntegrityVerdict:
        records = self._read_physical()
        return self._verify(records, expected_head=expected_head)

    def verify_export(
        self, records: tuple[AuditRecord, ...], *, expected_head: ChainHead | None = None
    ) -> IntegrityVerdict:
        """Verify an exported bundle (records already ordered by ``sequence``)."""
        return self._verify(records, expected_head=expected_head)

    @staticmethod
    def classify_break(verdict: IntegrityVerdict) -> BreakClass:
        return verdict.break_class if verdict.break_class is not None else BreakClass.INCONCLUSIVE

    @staticmethod
    def _verify(
        records: tuple[AuditRecord, ...], *, expected_head: ChainHead | None
    ) -> IntegrityVerdict:
        if not records:
            if expected_head is not None and expected_head.sequence >= 1:
                return _broken(BreakClass.TRUNCATION, None, "chain empty but a head was expected")
            return _valid()

        # 1) Genesis anchor.
        if records[0].predecessor_hash != GENESIS_ANCHOR:
            return _broken(
                BreakClass.BAD_ANCHOR, records[0].sequence, "first record has a non-genesis anchor"
            )

        # 2) Content integrity (rewrite): recompute every record hash.
        for rec in records:
            if rec.recompute_hash() != rec.record_hash:
                return _broken(
                    BreakClass.REWRITE, rec.sequence, "content does not match record_hash"
                )

        seqs = [r.sequence for r in records]
        n = len(records)

        # 3) Completeness (deletion): the sequence set must be exactly {1..n}.
        if sorted(seqs) != list(range(1, n + 1)):
            missing = sorted(set(range(1, n + 1)) - set(seqs))
            return _broken(
                BreakClass.DELETION,
                missing[0] if missing else None,
                f"sequence set is not contiguous {1}..{n}: {seqs}",
            )

        # 4) Physical order (reorder): physical order must equal sequence order.
        if seqs != sorted(seqs):
            return _broken(
                BreakClass.REORDER, None, f"physical order does not match sequence order: {seqs}"
            )

        # 5) Linkage: each record's predecessor_hash must equal the prior record's record_hash.
        #    (Catches a consistently re-forged record — the NEXT link then fails.)
        prev_hash = GENESIS_ANCHOR
        for rec in records:
            if rec.predecessor_hash != prev_hash:
                return _broken(
                    BreakClass.REORDER, rec.sequence, "predecessor_hash does not chain"
                )
            prev_hash = rec.record_hash

        # 6) Truncation: compare the actual tip against an externally-remembered head.
        if expected_head is not None:
            head = records[-1]
            if head.sequence < expected_head.sequence:
                return _broken(
                    BreakClass.TRUNCATION,
                    head.sequence,
                    f"head sequence {head.sequence} < expected {expected_head.sequence}",
                )
            same_seq = head.sequence == expected_head.sequence
            if same_seq and head.record_hash != expected_head.record_hash:
                return _broken(
                    BreakClass.REWRITE, head.sequence, "head record_hash differs from expected"
                )

        return _valid()


__all__ = ["AuditValidator"]
