"""Fenced expiring leases (PH-2, CMP-LEASE).

Fencing tokens are persistent, strictly increasing integers scoped to (resource_type, resource_id)
and stored in SQLite — never wall-clock timestamps and never ``time.monotonic()`` values (which
reset on process restart and cannot be compared across restarts, 01M §3.12/§3.19). A delayed owner
cannot write after its lease is superseded: only the current highest token, held under the current
process epoch and not released, validates. A lease from a prior process epoch is treated as expired
regardless of its wall-clock expiry — the primary cross-restart safety net (01M "no blind resume").
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from factory.orchestrator.errors import OrchestratorError
from factory.orchestrator.models import Lease, LeaseResourceType, ProcessEpoch


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class LeaseManager:
    database_path: Path
    process_epoch: ProcessEpoch

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        return connection

    def acquire(
        self, resource_type: LeaseResourceType, resource_id: str, owner_id: str, ttl_seconds: int
    ) -> Lease:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO fencing_counters (resource_type, resource_id, last_token) "
                "VALUES (?, ?, 1) "
                "ON CONFLICT(resource_type, resource_id) "
                "DO UPDATE SET last_token = last_token + 1",
                (resource_type.value, resource_id),
            )
            token_row = connection.execute(
                "SELECT last_token FROM fencing_counters "
                "WHERE resource_type = ? AND resource_id = ?",
                (resource_type.value, resource_id),
            ).fetchone()
            token = int(token_row["last_token"])
            now = datetime.now(UTC)
            acquired_at = _fmt(now)
            expires_at = _fmt(now + timedelta(seconds=ttl_seconds))
            connection.execute(
                "INSERT INTO leases (resource_type, resource_id, fencing_token, owner_id, "
                "process_epoch, acquired_at, expires_at, released) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    resource_type.value,
                    resource_id,
                    token,
                    owner_id,
                    self.process_epoch.value,
                    acquired_at,
                    expires_at,
                ),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("LEASE_TX_FAILED", f"acquire failed: {exc}") from exc
        finally:
            connection.close()
        return Lease(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            fencing_token=token,
            process_epoch=self.process_epoch.value,
            acquired_at=acquired_at,
            expires_at=expires_at,
            released=False,
        )

    def renew(self, lease: Lease, ttl_seconds: int) -> Lease:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if not self._is_current_owner(connection, lease):
                connection.rollback()
                raise OrchestratorError(
                    "STALE_LEASE",
                    f"cannot renew superseded/foreign lease for "
                    f"{lease.resource_type.value}:{lease.resource_id}",
                )
            expires_at = _fmt(datetime.now(UTC) + timedelta(seconds=ttl_seconds))
            connection.execute(
                "UPDATE leases SET expires_at = ? "
                "WHERE resource_type = ? AND resource_id = ? AND fencing_token = ?",
                (expires_at, lease.resource_type.value, lease.resource_id, lease.fencing_token),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("LEASE_TX_FAILED", f"renew failed: {exc}") from exc
        finally:
            connection.close()
        return Lease(
            resource_type=lease.resource_type,
            resource_id=lease.resource_id,
            owner_id=lease.owner_id,
            fencing_token=lease.fencing_token,
            process_epoch=lease.process_epoch,
            acquired_at=lease.acquired_at,
            expires_at=expires_at,
            released=False,
        )

    def release(self, lease: Lease) -> None:
        """Idempotent: releasing an already-released lease does not error or mint a new token."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE leases SET released = 1 "
                "WHERE resource_type = ? AND resource_id = ? AND fencing_token = ?",
                (lease.resource_type.value, lease.resource_id, lease.fencing_token),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise OrchestratorError("LEASE_TX_FAILED", f"release failed: {exc}") from exc
        finally:
            connection.close()

    def validate_token(
        self, resource_type: LeaseResourceType, resource_id: str, token: int
    ) -> bool:
        """A token is valid iff it is the current highest for the resource, held under this
        process epoch, and not released. A prior-epoch or superseded token is rejected."""
        connection = self._connect()
        try:
            counter = connection.execute(
                "SELECT last_token FROM fencing_counters "
                "WHERE resource_type = ? AND resource_id = ?",
                (resource_type.value, resource_id),
            ).fetchone()
            if counter is None or int(counter["last_token"]) != token:
                return False
            lease = connection.execute(
                "SELECT process_epoch, released FROM leases "
                "WHERE resource_type = ? AND resource_id = ? AND fencing_token = ?",
                (resource_type.value, resource_id, token),
            ).fetchone()
        finally:
            connection.close()
        if lease is None or bool(lease["released"]):
            return False
        return bool(lease["process_epoch"] == self.process_epoch.value)

    def _is_current_owner(self, connection: sqlite3.Connection, lease: Lease) -> bool:
        counter = connection.execute(
            "SELECT last_token FROM fencing_counters WHERE resource_type = ? AND resource_id = ?",
            (lease.resource_type.value, lease.resource_id),
        ).fetchone()
        if counter is None or int(counter["last_token"]) != lease.fencing_token:
            return False
        row = connection.execute(
            "SELECT process_epoch, released FROM leases "
            "WHERE resource_type = ? AND resource_id = ? AND fencing_token = ?",
            (lease.resource_type.value, lease.resource_id, lease.fencing_token),
        ).fetchone()
        if row is None or bool(row["released"]):
            return False
        return bool(row["process_epoch"] == self.process_epoch.value)


__all__ = ["LeaseManager"]
