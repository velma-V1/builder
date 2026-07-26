"""Audit-chain migrations + the append-only audit writer (roadmap PH-3, CMP-AUDITW).

CMP-AUDITW is the SOLE writer of the tamper-evident audit chain (an R1-analogue for the audit
domain). It appends only — no UPDATE/DELETE path exists — and computes every chain-identity field
(``sequence``, ``predecessor_hash``, ``record_hash``) itself, so a caller cannot forge chain
position (audit-writer-spec; 01K-AC-19). The chain lives in a separate PH-3 store, not the frozen
runtime-state DB (DEP-RPH3 §2). ``UNIQUE(op_key, record_kind)`` allows one ``INTENT`` + one
``COMPLETION`` per operation (XSC-RPH3 §2) while rejecting duplicate lifecycle records; a Class-3
``COMPLETION`` cannot precede its ``INTENT``.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from factory.audit.errors import AuditError
from factory.audit.models import (
    GENESIS_ANCHOR,
    AuditEvent,
    AuditRecord,
    ChainHead,
    RecordKind,
)

# Reuse the exact PH-1 SHA-256-pinned transactional migration mechanics (as CMP-ORCH does).
from factory.contracts.activation.store import (
    _MIGRATION_FILENAME,
    _apply_single_migration,
    _table_exists,
)

_EXPECTED_MIGRATION_HASHES: Mapping[str, str] = {
    "0001_audit_chain.sql": "935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433",
}

_MAX_SEQUENCE_RETRIES = 8

# Fully-literal SQL (no interpolation) so the append-only guarantee is the only trust surface and
# static analysis needs no exceptions (mirrors CMP-ORCH's store).
_INSERT_SQL = (
    "INSERT INTO audit_records "
    "(sequence, op_key, record_kind, operation_class, actor, action_class, target_ref, "
    "payload_hash, occurred_at, predecessor_hash, record_hash, signature) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
_SELECT_HEAD_SQL = (
    "SELECT record_id, sequence, op_key, record_kind, operation_class, actor, action_class, "
    "target_ref, payload_hash, occurred_at, predecessor_hash, record_hash, signature "
    "FROM audit_records ORDER BY sequence DESC LIMIT 1"
)
_SELECT_FROM_SQL = (
    "SELECT record_id, sequence, op_key, record_kind, operation_class, actor, action_class, "
    "target_ref, payload_hash, occurred_at, predecessor_hash, record_hash, signature "
    "FROM audit_records WHERE sequence >= ? ORDER BY sequence"
)
_SELECT_RANGE_SQL = (
    "SELECT record_id, sequence, op_key, record_kind, operation_class, actor, action_class, "
    "target_ref, payload_hash, occurred_at, predecessor_hash, record_hash, signature "
    "FROM audit_records WHERE sequence >= ? AND sequence <= ? ORDER BY sequence"
)


def apply_audit_migrations(database_path: Path, migrations_root: Path) -> None:
    """Apply the audit-store migrations transactionally with SHA-256 pinning (mirrors CMP-ORCH)."""
    files = sorted(migrations_root.glob("*.sql"))
    if not files:
        raise AuditError("MIGRATION_MISSING", f"no audit migrations found under {migrations_root}")

    connection = sqlite3.connect(str(database_path))
    try:
        applied: set[int] = set()
        if _table_exists(connection, "schema_migrations"):
            applied = {
                int(r[0])
                for r in connection.execute("SELECT version FROM schema_migrations")
            }

        for path in files:
            match = _MIGRATION_FILENAME.match(path.name)
            if not match:
                raise AuditError(
                    "MIGRATION_MALFORMED", f"malformed migration filename: {path.name}"
                )
            version = int(match.group(1))
            if version in applied:
                continue

            content = path.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            expected = _EXPECTED_MIGRATION_HASHES.get(path.name)
            if expected is None or actual != expected:
                raise AuditError(
                    "MIGRATION_INTEGRITY", f"migration integrity check failed for {path.name}"
                )
            try:
                _apply_single_migration(connection, content)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, path.name),
                )
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                raise AuditError(
                    "MIGRATION_FAILED", f"migration {path.name} failed to apply: {exc}"
                ) from exc
            applied.add(version)
    finally:
        connection.close()


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


@dataclass(frozen=True, slots=True)
class AuditWriter:
    """The sole append path to the audit chain."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.row_factory = sqlite3.Row
        return connection

    def head(self) -> AuditRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(_SELECT_HEAD_SQL).fetchone()
        finally:
            connection.close()
        return _row_to_record(row) if row is not None else None

    def chain_head(self) -> ChainHead | None:
        head = self.head()
        if head is None:
            return None
        return ChainHead(sequence=head.sequence, record_hash=head.record_hash)

    def export(self, *, start: int = 1, end: int | None = None) -> tuple[AuditRecord, ...]:
        """Return records in sequence order (integrity-checked on the way out by CMP-AUDITV)."""
        connection = self._connect()
        try:
            if end is None:
                rows = connection.execute(_SELECT_FROM_SQL, (start,)).fetchall()
            else:
                rows = connection.execute(_SELECT_RANGE_SQL, (start, end)).fetchall()
        finally:
            connection.close()
        return tuple(_row_to_record(r) for r in rows)

    def append(self, event: AuditEvent) -> AuditRecord:
        """Append one durable, hash-chained record. Sole append path; forge-resistant.

        Rejects (fail closed): a duplicate ``(op_key, record_kind)``; an ``INTENT`` for a
        non-Class-3 operation; a Class-3 ``COMPLETION`` with no prior ``INTENT``. On a concurrent
        sequence
        collision it retries against the fresh head (no gap/fork).
        """
        if event.operation_class not in (1, 2, 3):
            raise AuditError(
                "AUDIT_BAD_CLASS", f"invalid operation_class {event.operation_class!r}"
            )
        if event.record_kind is RecordKind.INTENT and event.operation_class != 3:
            raise AuditError(
                "AUDIT_INTENT_ONLY_CLASS3",
                "an INTENT record is only valid for a Class-3 operation",
            )

        last_error: sqlite3.IntegrityError | None = None
        for _ in range(_MAX_SEQUENCE_RETRIES):
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")

                # Duplicate lifecycle record → reject (UNIQUE also enforces; clear error first).
                dup = connection.execute(
                    "SELECT 1 FROM audit_records WHERE op_key = ? AND record_kind = ?",
                    (event.op_key, str(event.record_kind)),
                ).fetchone()
                if dup is not None:
                    connection.rollback()
                    raise AuditError(
                        "AUDIT_DUPLICATE",
                        f"a {event.record_kind} record already exists for op_key {event.op_key}",
                    )

                # Class-3 completion cannot precede its intent.
                if event.operation_class == 3 and event.record_kind is RecordKind.COMPLETION:
                    intent = connection.execute(
                        "SELECT 1 FROM audit_records WHERE op_key = ? AND record_kind = 'INTENT'",
                        (event.op_key,),
                    ).fetchone()
                    if intent is None:
                        connection.rollback()
                        raise AuditError(
                            "AUDIT_COMPLETION_BEFORE_INTENT",
                            f"Class-3 COMPLETION for op_key {event.op_key} has no prior INTENT",
                        )

                head_row = connection.execute(
                    "SELECT sequence, record_hash FROM audit_records ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if head_row is None else int(head_row["sequence"]) + 1
                predecessor_hash = GENESIS_ANCHOR if head_row is None else head_row["record_hash"]

                record_hash = AuditRecord.compute_hash(
                    sequence=sequence,
                    op_key=event.op_key,
                    record_kind=event.record_kind,
                    operation_class=event.operation_class,
                    actor=event.actor,
                    action_class=event.action_class,
                    target_ref=event.target_ref,
                    payload_hash=event.payload_hash,
                    occurred_at=event.occurred_at,
                    predecessor_hash=predecessor_hash,
                )

                cursor = connection.execute(
                    _INSERT_SQL,
                    (
                        sequence,
                        event.op_key,
                        str(event.record_kind),
                        event.operation_class,
                        event.actor,
                        event.action_class,
                        event.target_ref,
                        event.payload_hash,
                        event.occurred_at,
                        predecessor_hash,
                        record_hash,
                        None,
                    ),
                )
                record_id = int(cursor.lastrowid) if cursor.lastrowid is not None else -1
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                message = str(exc)
                if "op_key" in message or "record_kind" in message:
                    raise AuditError(
                        "AUDIT_DUPLICATE",
                        f"a {event.record_kind} record already exists for op_key {event.op_key}",
                    ) from exc
                # sequence / record_hash collision under concurrency → retry against fresh head.
                last_error = exc
                continue
            except sqlite3.Error as exc:
                connection.rollback()
                raise AuditError("AUDIT_APPEND_FAILED", f"audit append failed: {exc}") from exc
            finally:
                connection.close()

            return AuditRecord(
                record_id=record_id,
                sequence=sequence,
                op_key=event.op_key,
                record_kind=event.record_kind,
                operation_class=event.operation_class,
                actor=event.actor,
                action_class=event.action_class,
                target_ref=event.target_ref,
                payload_hash=event.payload_hash,
                occurred_at=event.occurred_at,
                predecessor_hash=predecessor_hash,
                record_hash=record_hash,
                signature=None,
            )

        raise AuditError(
            "AUDIT_APPEND_CONTENDED",
            f"audit append could not obtain a unique sequence after retries: {last_error}",
        )


__all__ = ["AuditWriter", "apply_audit_migrations"]
