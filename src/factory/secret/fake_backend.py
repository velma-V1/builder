"""Deterministic fake secret backend (preinstallation stand-in for Task 5.3).

Fully in-memory and offline. Materializes task-scoped, TTL-bounded, revocable leases; redacts active
material from text; scans for secrets before an export; and revokes-and-forgets on task disposal so
**no secret material persists** past its lease (``01E §3.4``). The live broker (real short-lived
credential issuance) is LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

from collections.abc import Mapping

from factory.secret.errors import SecretError
from factory.secret.models import SecretLease, SecretRef
from factory.secret.redaction import contains_secret, redact


class FakeSecretBackend:
    """Configurable deterministic secret broker for tests and the preinstallation core."""

    __slots__ = ("_leases", "_material")

    def __init__(self, material: Mapping[str, str]) -> None:
        # Configured ref_id -> secret value: the upstream secret store, not persisted runtime state.
        self._material: dict[str, str] = dict(material)
        self._leases: dict[str, SecretLease] = {}

    def inject(self, ref: SecretRef, now: int) -> SecretLease:
        if ref.ref_id not in self._material:
            raise SecretError("SECRET_UNKNOWN", f"no secret material for ref {ref.ref_id}")
        if ref.max_ttl <= 0:
            raise SecretError("SECRET_TTL_INVALID", "secret TTL must be positive")
        lease = SecretLease(
            ref_id=ref.ref_id,
            name=ref.name,
            value=self._material[ref.ref_id],
            task_id=ref.task_id,
            granted_at=now,
            expires_at=now + ref.max_ttl,
        )
        self._leases[ref.ref_id] = lease
        return lease

    def revoke(self, ref_id: str) -> bool:
        lease = self._leases.get(ref_id)
        if lease is None or lease.revoked:
            return False
        # Revoke-and-forget: the materialized value is dropped, not retained.
        self._leases.pop(ref_id)
        return True

    def revoke_task(self, task_id: str) -> int:
        to_revoke = [rid for rid, lease in self._leases.items() if lease.task_id == task_id]
        for ref_id in to_revoke:
            self._leases.pop(ref_id)
        return len(to_revoke)

    def active_values(self, now: int) -> tuple[str, ...]:
        return tuple(lease.value for lease in self._leases.values() if lease.is_active(now))

    def redact(self, text: str, now: int) -> str:
        return redact(text, self.active_values(now))

    def scan_export(self, text: str) -> None:
        """Pre-export secret scan (``01E §3.4``): any known material in ``text`` blocks export."""
        if contains_secret(text, self._material.values()):
            raise SecretError("SECRET_IN_EXPORT", "secret material detected in export; blocked")

    def has_persisted_material(self, now: int) -> bool:
        """True only if an active lease remains — used to assert no secret survives disposal."""
        return any(lease.is_active(now) for lease in self._leases.values())
