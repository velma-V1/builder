"""Private sole-writer for the approval domain (CMP-APPROVAL, DEP-RPH3 §4A).

``_ApprovalWriter`` encapsulates the only writable connection to ``approval_records``,
``approval_queue`` and ``approval_intents`` and is **never exported** (mirrors PH-2's un-exported
``_OrchestratorStateWriter``). Its connection installs a structural SQLite authorizer that denies
any write outside those three tables, so even a bug cannot mutate another domain's tables.

It exposes only the XSC-RPH3 Class-1 primitives the engine composes — *stage* (durable intent + a
non-authoritative ``PENDING`` mutation), *commit* (flip to ``COMMITTED`` after the completion audit
is durable) and *rollback* (undo a mutation whose audit never became durable). Ordering and audit
calls live in the engine; this module only performs the two short single-domain transactions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.approval.errors import ApprovalError
from factory.approval.models import ApprovalState
from factory.approval.store import _approval_writer_authorizer


@dataclass(frozen=True, slots=True)
class _StagedRecord:
    state: str
    uses_consumed: int


@dataclass(frozen=True, slots=True)
class _ApprovalWriter:
    """Sole writer of the approval tables. Not exported; the engine holds the only reference."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_approval_writer_authorizer)
        return connection

    def stage_enqueue(
        self,
        *,
        approval_id: str,
        op_key: str,
        task_id: str,
        tool: str,
        action: str,
        resource: str | None,
        scope: str,
        purpose: str,
        consequences: str,
        autonomy_level: str,
        repetition_limit: int,
        requires_confirmation: bool,
        expires_at: int,
        ts: int,
    ) -> None:
        """S1+S2 for enqueue: durable intent + a non-authoritative PENDING record + queue row."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO approval_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, created_ts, updated_ts) "
                "VALUES (?, 1, 'approval', ?, 'enqueue', 'PENDING', 'NONE', ?, ?)",
                (op_key, approval_id, ts, ts),
            )
            connection.execute(
                "INSERT INTO approval_records (approval_id, state, commit_state, prior_state, "
                "task_id, tool, action, resource, scope, purpose, consequences, autonomy_level, "
                "repetition_limit, uses_consumed, requires_confirmation, expires_at, "
                "action_fingerprint, created_ts, updated_ts) "
                "VALUES (?, 'PENDING', 'PENDING', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, "
                "?, ?)",
                (
                    approval_id,
                    task_id,
                    tool,
                    action,
                    resource,
                    scope,
                    purpose,
                    consequences,
                    autonomy_level,
                    repetition_limit,
                    1 if requires_confirmation else 0,
                    expires_at,
                    ts,
                    ts,
                ),
            )
            connection.execute(
                "INSERT INTO approval_queue (approval_id, enqueued_ts) VALUES (?, ?)",
                (approval_id, ts),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ApprovalError("APPROVAL_STAGE_FAILED", f"enqueue stage failed: {exc}") from exc
        finally:
            connection.close()

    def stage_transition(
        self,
        *,
        approval_id: str,
        op_key: str,
        verb: str,
        new_state: ApprovalState,
        ts: int,
        action_fingerprint: str | None = None,
        increment_use: bool = False,
    ) -> None:
        """S1+S2 for a lifecycle transition: durable intent + a non-authoritative PENDING mutation.

        Records ``prior_state`` (the current committed state) so a rollback can restore it if the
        completion audit never becomes durable.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT state, uses_consumed FROM approval_records WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if current is None:
                connection.rollback()
                raise ApprovalError(
                    "APPROVAL_NOT_FOUND", f"no approval record for {approval_id}"
                )
            connection.execute(
                "INSERT INTO approval_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, created_ts, updated_ts) "
                "VALUES (?, 1, 'approval', ?, ?, 'PENDING', 'NONE', ?, ?)",
                (op_key, approval_id, verb, ts, ts),
            )
            # The increment is a bound parameter (0 or 1), never string-interpolated SQL.
            use_delta = 1 if increment_use else 0
            if action_fingerprint is not None:
                connection.execute(
                    "UPDATE approval_records SET prior_state = state, state = ?, "
                    "commit_state = 'PENDING', action_fingerprint = ?, "
                    "uses_consumed = uses_consumed + ?, updated_ts = ? WHERE approval_id = ?",
                    (str(new_state), action_fingerprint, use_delta, ts, approval_id),
                )
            else:
                connection.execute(
                    "UPDATE approval_records SET prior_state = state, state = ?, "
                    "commit_state = 'PENDING', uses_consumed = uses_consumed + ?, updated_ts = ? "
                    "WHERE approval_id = ?",
                    (str(new_state), use_delta, ts, approval_id),
                )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ApprovalError(
                "APPROVAL_STAGE_FAILED", f"{verb} stage failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def commit_operation(
        self, *, approval_id: str, op_key: str, audit_seq: int, ts: int, drop_queue: bool
    ) -> None:
        """S4: flip the mutation to COMMITTED once its completion audit is durable (roll fwd)."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE approval_records SET commit_state = 'COMMITTED', prior_state = NULL, "
                "updated_ts = ? WHERE approval_id = ?",
                (ts, approval_id),
            )
            connection.execute(
                "UPDATE approval_intents SET status = 'COMMITTED', "
                "reconciliation_state = 'ROLL_FORWARD', audit_seq = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (audit_seq, ts, ts, op_key),
            )
            if drop_queue:
                connection.execute(
                    "DELETE FROM approval_queue WHERE approval_id = ?", (approval_id,)
                )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ApprovalError(
                "APPROVAL_COMMIT_FAILED", f"commit of {op_key} failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def rollback_operation(
        self, *, approval_id: str, op_key: str, verb: str, failure_code: str, ts: int
    ) -> None:
        """Undo a mutation whose completion audit never became durable (Class-1 roll-back).

        ``enqueue`` roll-back deletes the never-authoritative record + queue row (it never existed
        for readers, INV-2). Any other verb restores ``prior_state`` and, for ``consume``, undoes
        the use it had staged. Idempotent on ``op_key`` so a re-run reconciliation is safe.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if verb == "enqueue":
                connection.execute(
                    "DELETE FROM approval_queue WHERE approval_id = ?", (approval_id,)
                )
                connection.execute(
                    "DELETE FROM approval_records WHERE approval_id = ?", (approval_id,)
                )
            else:
                # Undo the staged use (bound parameter): -1 for a consume, 0 otherwise.
                use_delta = 1 if verb == "consume" else 0
                connection.execute(
                    "UPDATE approval_records SET state = prior_state, commit_state = 'COMMITTED', "
                    "prior_state = NULL, uses_consumed = uses_consumed - ?, updated_ts = ? "
                    "WHERE approval_id = ? AND prior_state IS NOT NULL",
                    (use_delta, ts, approval_id),
                )
            connection.execute(
                "UPDATE approval_intents SET status = 'ABORTED', "
                "reconciliation_state = 'ROLL_BACK', failure_code = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (failure_code, ts, ts, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ApprovalError(
                "APPROVAL_ROLLBACK_FAILED", f"rollback of {op_key} failed: {exc}"
            ) from exc
        finally:
            connection.close()


__all__ = ["_ApprovalWriter"]
