"""Core project-authority memory records (PH-2, CMP-MEM — partial scope).

Implements ONLY the PROJECT_AUTHORITY memory class (01F §3): provenance, a status lifecycle
(PROPOSED/VERIFIED/SUPERSEDED/REFUTED/ARCHIVED), and versioned correction — a correction never
edits a row in place; it inserts a new record linked to the prior one via `supersedes` and marks the
prior row SUPERSEDED (01F §2.9). No other memory class (active task context, user preferences,
global knowledge, raw sessions, derived retrieval data) is implemented here — deferred to PH-7.

`MemoryRecord` has no free-form value field, only reference-shaped fields (source, scope, a bounded
summary, an optional evidence_ref) — secrets cannot be stored because there is nowhere to put one
(01F §2.16), enforced structurally rather than by a runtime scan.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import MemoryRecord, MemoryRecordStatus

_SELECT_BY_ID_SQL = (
    "SELECT record_id, project_id, memory_class, status, source, scope, summary, "
    "evidence_ref, supersedes, created_at FROM memory_records WHERE record_id = ?"
)
_INSERT_SQL = (
    "INSERT INTO memory_records (record_id, project_id, memory_class, status, source, "
    "scope, summary, evidence_ref, supersedes, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        record_id=row["record_id"],
        project_id=row["project_id"],
        memory_class=row["memory_class"],
        status=MemoryRecordStatus(row["status"]),
        source=row["source"],
        scope=row["scope"],
        summary=row["summary"],
        evidence_ref=row["evidence_ref"],
        supersedes=row["supersedes"],
        created_at=row["created_at"],
    )


def _record_values(record: MemoryRecord) -> tuple[object, ...]:
    return (
        record.record_id,
        record.project_id,
        record.memory_class,
        record.status.value,
        record.source,
        record.scope,
        record.summary,
        record.evidence_ref,
        record.supersedes,
        record.created_at,
    )


@dataclass(slots=True)
class MemoryStore:
    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def propose(self, record: MemoryRecord) -> MemoryRecord:
        if record.status is not MemoryRecordStatus.PROPOSED:
            raise OrchestratorError(
                "MEMORY_INVALID_STATUS", "a newly proposed record must have status PROPOSED"
            )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_INSERT_SQL, _record_values(record))
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("MEMORY_TX_FAILED", f"propose failed: {exc}") from exc
        finally:
            connection.close()
        return record

    def verify(self, record_id: str) -> MemoryRecord:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(_SELECT_BY_ID_SQL, (record_id,)).fetchone()
            if row is None:
                connection.rollback()
                raise OrchestratorError("MEMORY_NOT_FOUND", f"record {record_id} not found")
            if row["status"] != MemoryRecordStatus.PROPOSED.value:
                connection.rollback()
                raise OrchestratorError(
                    "MEMORY_INVALID_TRANSITION",
                    f"cannot verify a record with status {row['status']}",
                )
            connection.execute(
                "UPDATE memory_records SET status = ? WHERE record_id = ?",
                (MemoryRecordStatus.VERIFIED.value, record_id),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("MEMORY_TX_FAILED", f"verify failed: {exc}") from exc
        finally:
            connection.close()
        record = self.get(record_id)
        assert record is not None  # just verified; must exist
        return record

    def supersede(self, record_id: str, new_record: MemoryRecord) -> MemoryRecord:
        if new_record.supersedes != record_id:
            raise OrchestratorError(
                "MEMORY_INVALID_SUPERSESSION", "new_record.supersedes must equal record_id"
            )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT status FROM memory_records WHERE record_id = ?", (record_id,)
            ).fetchone()
            if prior is None:
                connection.rollback()
                raise OrchestratorError("MEMORY_NOT_FOUND", f"record {record_id} not found")
            # Never edit in place: insert the new record, then mark the prior SUPERSEDED.
            connection.execute(_INSERT_SQL, _record_values(new_record))
            connection.execute(
                "UPDATE memory_records SET status = ? WHERE record_id = ?",
                (MemoryRecordStatus.SUPERSEDED.value, record_id),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("MEMORY_TX_FAILED", f"supersede failed: {exc}") from exc
        finally:
            connection.close()
        return new_record

    def get(self, record_id: str) -> MemoryRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(_SELECT_BY_ID_SQL, (record_id,)).fetchone()
        finally:
            connection.close()
        return _row_to_record(row) if row is not None else None


__all__ = ["MemoryStore"]
