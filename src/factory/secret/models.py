"""Value objects for the PH-5 secret broker (``01E §3.4``, CTR-SECRET-REF).

A :class:`SecretRef` is a task-scoped *reference* with a bounded TTL — never the material itself.
A :class:`SecretLease` is the short-lived, revocable materialization injected at execution time. The
material never lives in a contract, cache, checkpoint, or export.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SecretRef:
    """A task-scoped reference to a secret (CTR-SECRET-REF). Carries no material."""

    ref_id: str
    name: str
    task_id: str
    max_ttl: int


@dataclass(frozen=True, slots=True)
class SecretLease:
    """A short-lived, revocable injection of secret material for one task."""

    ref_id: str
    name: str
    value: str
    task_id: str
    granted_at: int
    expires_at: int
    revoked: bool = False

    def is_active(self, now: int) -> bool:
        return not self.revoked and now < self.expires_at
