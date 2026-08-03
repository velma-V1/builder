"""Private sole-writer for the permission domain (CMP-PERM, DEP-RPH3 §4A).

``_PermissionWriter`` encapsulates the only writable connection to ``permission_grants`` and
``permission_intents`` and is **never exported**. Its connection installs a structural SQLite
authorizer that denies any write outside those two tables (including approval tables). It exposes
the XSC-RPH3 Class-1 primitives the engine composes — *stage* (durable intent + a non-authoritative
``PENDING`` mutation), *commit* (flip to ``COMMITTED`` once the completion audit is durable), and
*rollback* (undo a mutation whose audit never became durable).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.permission.errors import PermissionError
from factory.permission.models import PermissionClass, PermissionState
from factory.permission.store import _permission_writer_authorizer


@dataclass(frozen=True, slots=True)
class _PermissionWriter:
    """Sole writer of the permission tables. Not exported; the engine holds the only reference."""

    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_permission_writer_authorizer)
        return connection

    def stage_issue(
        self,
        *,
        grant_id: str,
        op_key: str,
        task_id: str,
        tool: str,
        action: str,
        permission_class: PermissionClass,
        resource: str | None,
        scope: str,
        purpose: str,
        grant_fingerprint: str,
        expires_at: int,
        ts: int,
    ) -> None:
        """S1+S2 for grant issue: durable intent + a non-authoritative PENDING/ACTIVE grant."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO permission_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, created_ts, updated_ts) "
                "VALUES (?, 1, 'permission', ?, 'issue', 'PENDING', 'NONE', ?, ?)",
                (op_key, grant_id, ts, ts),
            )
            connection.execute(
                "INSERT INTO permission_grants (grant_id, state, commit_state, prior_state, "
                "task_id, tool, action, permission_class, resource, scope, purpose, "
                "grant_fingerprint, expires_at, created_ts, updated_ts) "
                "VALUES (?, 'ACTIVE', 'PENDING', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    grant_id,
                    task_id,
                    tool,
                    action,
                    str(permission_class),
                    resource,
                    scope,
                    purpose,
                    grant_fingerprint,
                    expires_at,
                    ts,
                    ts,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise PermissionError("PERMISSION_STAGE_FAILED", f"issue stage failed: {exc}") from exc
        finally:
            connection.close()

    def stage_transition(
        self, *, grant_id: str, op_key: str, verb: str, new_state: PermissionState, ts: int
    ) -> None:
        """S1+S2 for a grant transition: durable intent + a non-authoritative PENDING mutation.

        Records ``prior_state`` so a rollback can restore it if the completion audit never lands.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT state FROM permission_grants WHERE grant_id = ?", (grant_id,)
            ).fetchone()
            if current is None:
                connection.rollback()
                raise PermissionError("PERMISSION_NOT_FOUND", f"no grant {grant_id}")
            connection.execute(
                "INSERT INTO permission_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, created_ts, updated_ts) "
                "VALUES (?, 1, 'permission', ?, ?, 'PENDING', 'NONE', ?, ?)",
                (op_key, grant_id, verb, ts, ts),
            )
            connection.execute(
                "UPDATE permission_grants SET prior_state = state, state = ?, "
                "commit_state = 'PENDING', updated_ts = ? WHERE grant_id = ?",
                (str(new_state), ts, grant_id),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise PermissionError("PERMISSION_STAGE_FAILED", f"{verb} stage failed: {exc}") from exc
        finally:
            connection.close()

    def commit_operation(self, *, grant_id: str, op_key: str, audit_seq: int, ts: int) -> None:
        """S4: flip the mutation to COMMITTED once its completion audit is durable (roll fwd)."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE permission_grants SET commit_state = 'COMMITTED', prior_state = NULL, "
                "updated_ts = ? WHERE grant_id = ?",
                (ts, grant_id),
            )
            connection.execute(
                "UPDATE permission_intents SET status = 'COMMITTED', "
                "reconciliation_state = 'ROLL_FORWARD', audit_seq = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (audit_seq, ts, ts, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise PermissionError(
                "PERMISSION_COMMIT_FAILED", f"commit of {op_key} failed: {exc}"
            ) from exc
        finally:
            connection.close()

    def rollback_operation(
        self, *, grant_id: str, op_key: str, verb: str, failure_code: str, ts: int
    ) -> None:
        """Undo a mutation whose completion audit never became durable (Class-1 roll-back).

        ``issue`` roll-back deletes the never-authoritative grant (INV-2); any other verb restores
        ``prior_state``. Idempotent on ``op_key`` so a re-run reconciliation is safe.
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if verb == "issue":
                connection.execute("DELETE FROM permission_grants WHERE grant_id = ?", (grant_id,))
            else:
                connection.execute(
                    "UPDATE permission_grants SET state = prior_state, commit_state = 'COMMITTED', "
                    "prior_state = NULL, updated_ts = ? "
                    "WHERE grant_id = ? AND prior_state IS NOT NULL",
                    (ts, grant_id),
                )
            connection.execute(
                "UPDATE permission_intents SET status = 'ABORTED', "
                "reconciliation_state = 'ROLL_BACK', failure_code = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (failure_code, ts, ts, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise PermissionError(
                "PERMISSION_ROLLBACK_FAILED", f"rollback of {op_key} failed: {exc}"
            ) from exc
        finally:
            connection.close()


__all__ = ["_PermissionWriter"]
