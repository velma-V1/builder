"""Private sole-writer for the tool domain (CMP-TOOLREG, DEP-RPH3 §4A).

``_ToolWriter`` encapsulates the only writable connection to the four tool tables and is **never
exported**. Its connection installs a structural SQLite authorizer denying any write outside those
tables (including approval/permission tables). It exposes the XSC-RPH3 Class-1 primitives the
registry composes. Quarantine/release history (``tool_quarantine``) is written at **commit** and
reconstructed from the intent's stashed ``detail``, so a reconcile roll-forward is faithful.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.tools.errors import ToolError
from factory.tools.models import ToolState
from factory.tools.store import _tool_writer_authorizer

_SEP = "\x1f"


def _target_ref(tool_id: str, version: str) -> str:
    return f"{tool_id}{_SEP}{version}"


@dataclass(frozen=True, slots=True)
class _ToolWriter:
    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        connection.set_authorizer(_tool_writer_authorizer)
        return connection

    def stage_register(
        self,
        *,
        tool_id: str,
        version: str,
        op_key: str,
        declaration_hash: str,
        provenance_source: str,
        provenance_checksum: str,
        license: str,
        declaration_json: str,
        output_schema_json: str,
        ts: int,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO tool_registry_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, created_ts, updated_ts) "
                "VALUES (?, 1, 'tool', ?, 'register', 'PENDING', 'NONE', ?, ?)",
                (op_key, _target_ref(tool_id, version), ts, ts),
            )
            connection.execute(
                "INSERT INTO tool_registry (tool_id, version, state, commit_state, prior_state, "
                "declaration_hash, provenance_source, provenance_checksum, license, failure_count, "
                "created_ts, updated_ts) "
                "VALUES (?, ?, 'REGISTERED', 'PENDING', NULL, ?, ?, ?, ?, 0, ?, ?)",
                (
                    tool_id,
                    version,
                    declaration_hash,
                    provenance_source,
                    provenance_checksum,
                    license,
                    ts,
                    ts,
                ),
            )
            connection.execute(
                "INSERT INTO tool_declarations (tool_id, version, declaration_json, "
                "output_schema_json, created_ts) VALUES (?, ?, ?, ?, ?)",
                (tool_id, version, declaration_json, output_schema_json, ts),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ToolError("TOOL_STAGE_FAILED", f"register stage failed: {exc}") from exc
        finally:
            connection.close()

    def stage_transition(
        self,
        *,
        tool_id: str,
        version: str,
        op_key: str,
        verb: str,
        new_state: ToolState,
        ts: int,
        detail: str | None = None,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT state FROM tool_registry WHERE tool_id = ? AND version = ?",
                (tool_id, version),
            ).fetchone()
            if current is None:
                connection.rollback()
                raise ToolError("TOOL_NOT_FOUND", f"no tool {tool_id}@{version}")
            connection.execute(
                "INSERT INTO tool_registry_intents (op_key, operation_class, domain, target_ref, "
                "requested_action, status, reconciliation_state, quarantine_state, created_ts, "
                "updated_ts) VALUES (?, 1, 'tool', ?, ?, 'PENDING', 'NONE', ?, ?, ?)",
                (op_key, _target_ref(tool_id, version), verb, detail, ts, ts),
            )
            connection.execute(
                "UPDATE tool_registry SET prior_state = state, state = ?, "
                "commit_state = 'PENDING', "
                "updated_ts = ? WHERE tool_id = ? AND version = ?",
                (str(new_state), ts, tool_id, version),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ToolError("TOOL_STAGE_FAILED", f"{verb} stage failed: {exc}") from exc
        finally:
            connection.close()

    def commit_operation(
        self, *, tool_id: str, version: str, op_key: str, audit_seq: int, ts: int
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            intent = connection.execute(
                "SELECT requested_action, quarantine_state FROM tool_registry_intents "
                "WHERE op_key = ?",
                (op_key,),
            ).fetchone()
            verb = None if intent is None else str(intent["requested_action"])
            detail = (
                None
                if intent is None or intent["quarantine_state"] is None
                else str(intent["quarantine_state"])
            )
            connection.execute(
                "UPDATE tool_registry SET commit_state = 'COMMITTED', prior_state = NULL, "
                "updated_ts = ? WHERE tool_id = ? AND version = ?",
                (ts, tool_id, version),
            )
            if verb == "quarantine":
                connection.execute(
                    "INSERT INTO tool_quarantine (tool_id, version, reason, quarantined_ts) "
                    "VALUES (?, ?, ?, ?)",
                    (tool_id, version, detail or "unspecified", ts),
                )
            elif verb == "release":
                connection.execute(
                    "UPDATE tool_quarantine SET released_ts = ?, review_ref = ? "
                    "WHERE tool_id = ? AND version = ? AND released_ts IS NULL",
                    (ts, detail, tool_id, version),
                )
            connection.execute(
                "UPDATE tool_registry_intents SET status = 'COMMITTED', "
                "reconciliation_state = 'ROLL_FORWARD', audit_seq = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (audit_seq, ts, ts, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ToolError("TOOL_COMMIT_FAILED", f"commit of {op_key} failed: {exc}") from exc
        finally:
            connection.close()

    def rollback_operation(
        self, *, tool_id: str, version: str, op_key: str, verb: str, failure_code: str, ts: int
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if verb == "register":
                connection.execute(
                    "DELETE FROM tool_declarations WHERE tool_id = ? AND version = ?",
                    (tool_id, version),
                )
                connection.execute(
                    "DELETE FROM tool_registry WHERE tool_id = ? AND version = ?",
                    (tool_id, version),
                )
            else:
                connection.execute(
                    "UPDATE tool_registry SET state = prior_state, commit_state = 'COMMITTED', "
                    "prior_state = NULL, updated_ts = ? "
                    "WHERE tool_id = ? AND version = ? AND prior_state IS NOT NULL",
                    (ts, tool_id, version),
                )
            connection.execute(
                "UPDATE tool_registry_intents SET status = 'ABORTED', "
                "reconciliation_state = 'ROLL_BACK', failure_code = ?, completed_ts = ?, "
                "updated_ts = ? WHERE op_key = ?",
                (failure_code, ts, ts, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ToolError("TOOL_ROLLBACK_FAILED", f"rollback of {op_key} failed: {exc}") from exc
        finally:
            connection.close()

    def increment_failure(self, *, tool_id: str, version: str, ts: int) -> int:
        """Bump the equivalent-failure counter (a heuristic, not an authority-granting write)."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE tool_registry SET failure_count = failure_count + 1, updated_ts = ? "
                "WHERE tool_id = ? AND version = ?",
                (ts, tool_id, version),
            )
            row = connection.execute(
                "SELECT failure_count FROM tool_registry WHERE tool_id = ? AND version = ?",
                (tool_id, version),
            ).fetchone()
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ToolError("TOOL_FAILURE_COUNT_FAILED", f"failure count failed: {exc}") from exc
        finally:
            connection.close()
        return 0 if row is None else int(row["failure_count"])


__all__ = ["_ToolWriter"]
