"""Private sole writer for the orchestrator-side WIR intervention journal."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from factory.watchdog.errors import WatchdogError
from factory.watchdog.models import (
    InterventionOutcome,
    InterventionRequest,
    InterventionStatus,
    ReconciliationState,
)
from factory.watchdog.store import _intervention_writer_authorizer


@dataclass(frozen=True, slots=True)
class _InterventionWriter:
    database_path: Path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.set_authorizer(_intervention_writer_authorizer)
        return connection

    def stage(
        self,
        request: InterventionRequest,
        operation_class: int,
        now: int,
        *,
        desired_state: str | None = None,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO watchdog_intervention_journal "
                "(op_key, operation_class, domain, target_ref, requested_action, status, "
                "reconciliation_state, request_hash, expected_state, desired_state, "
                "created_ts, updated_ts) "
                "VALUES (?, ?, 'watchdog', ?, ?, 'PENDING', 'NONE', ?, ?, ?, ?, ?)",
                (
                    request.idempotency_key,
                    operation_class,
                    request.target_ref,
                    str(request.command),
                    request.request_hash(),
                    request.expected_state,
                    desired_state,
                    now,
                    now,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WatchdogError(
                "INTERVENTION_STAGE_FAILED", f"could not persist intent: {exc}"
            ) from exc
        finally:
            connection.close()

    def finish(
        self,
        op_key: str,
        *,
        status: InterventionStatus,
        reconciliation: ReconciliationState,
        outcome: InterventionOutcome,
        cause: str,
        audit_seq: int | None,
        failure_code: str | None,
        now: int,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE watchdog_intervention_journal SET status = ?, "
                "reconciliation_state = ?, result_outcome = ?, result_cause = ?, "
                "audit_seq = ?, failure_code = ?, updated_ts = ?, completed_ts = ? "
                "WHERE op_key = ?",
                (
                    str(status),
                    str(reconciliation),
                    str(outcome),
                    cause,
                    audit_seq,
                    failure_code,
                    now,
                    now,
                    op_key,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WatchdogError(
                "INTERVENTION_COMMIT_FAILED", f"could not finish {op_key}: {exc}"
            ) from exc
        finally:
            connection.close()

    def mark_audit_intent(self, op_key: str, audit_seq: int, now: int) -> None:
        connection = self._connect()
        try:
            connection.execute(
                "UPDATE watchdog_intervention_journal SET audit_seq = ?, updated_ts = ? "
                "WHERE op_key = ?",
                (audit_seq, now, op_key),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise WatchdogError(
                "INTERVENTION_INTENT_MARK_FAILED", f"could not mark audit intent: {exc}"
            ) from exc
        finally:
            connection.close()


__all__: list[str] = []
