"""Secret broker interface (Task 5.3, ``01E §3.4``)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from factory.secret.models import SecretLease, SecretRef


@runtime_checkable
class SecretBroker(Protocol):
    """Brokered, scoped, revocable secret injection with redaction.

    * ``inject(ref, now)`` — materialize a short-lived lease for a task.
    * ``revoke(ref_id)`` — revoke a lease (True if one was active).
    * ``revoke_task(task_id)`` — revoke every lease for a task before disposal/export.
    * ``active_values(now)`` — currently-active secret material (for redaction).
    * ``redact(text, now)`` — replace active secret material in text.
    """

    def inject(self, ref: SecretRef, now: int) -> SecretLease: ...
    def revoke(self, ref_id: str) -> bool: ...
    def revoke_task(self, task_id: str) -> int: ...
    def active_values(self, now: int) -> tuple[str, ...]: ...
    def redact(self, text: str, now: int) -> str: ...
