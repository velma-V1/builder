from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.activation.store import _reader_authorizer
from factory.promotion.errors import PromotionError
from factory.promotion.models import PromotionOutcome, PromotionRecord


def _row(row: sqlite3.Row) -> PromotionRecord:
    return PromotionRecord(
        promotion_id=row["promotion_id"],
        task_id=row["task_id"],
        run_id=row["run_id"],
        approval_card_id=row["approval_card_id"],
        decided_by=row["decided_by"],
        promoted_branch=row["promoted_branch"],
        promoted_commit_sha=row["promoted_commit_sha"],
        outcome=PromotionOutcome(row["outcome"]),
        reason=row["reason"],
        created_at=row["created_at"],
    )


@dataclass(frozen=True, slots=True)
class SQLitePromotionReader:
    database_path: Path

    def get(self, promotion_id: str) -> PromotionRecord | None:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        try:
            row = connection.execute(
                "SELECT * FROM promotion_records WHERE promotion_id = ?", (promotion_id,)
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else _row(row)

    def get_latest_for_task(self, task_id: str) -> PromotionRecord | None:
        connection = sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_reader_authorizer)
        try:
            row = connection.execute(
                "SELECT * FROM promotion_records WHERE task_id = ? ORDER BY rowid DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else _row(row)


@dataclass(frozen=True, slots=True)
class _PromotionWriter:
    database_path: Path

    def record(self, record: PromotionRecord) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM promotion_records WHERE promotion_id = ?", (record.promotion_id,)
            ).fetchone()
            if existing is not None:
                connection.rollback()
                return
            connection.execute(
                "INSERT INTO promotion_records (promotion_id, task_id, run_id, approval_card_id, "
                "decided_by, promoted_branch, promoted_commit_sha, outcome, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.promotion_id,
                    record.task_id,
                    record.run_id,
                    record.approval_card_id,
                    record.decided_by,
                    record.promoted_branch,
                    record.promoted_commit_sha,
                    record.outcome.value,
                    record.reason,
                    record.created_at,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise PromotionError("PROMOTION_RECORD_FAILED", str(exc)) from exc
        finally:
            connection.close()
