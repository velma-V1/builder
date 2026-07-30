"""PH-5 (Task 5.3) — secret broker (preinstallation).

Broker interface + deterministic fake backend: task-scoped, TTL-bounded, revocable leases; redaction
of active material; pre-export secret scanning; and revoke-and-forget disposal so no secret material
persists (``01E §3.4``, CTR-SECRET-REF). Live credential issuance is LIVE_SANDBOX_PENDING.
"""

from __future__ import annotations

from factory.secret.broker import SecretBroker
from factory.secret.errors import SecretError
from factory.secret.fake_backend import FakeSecretBackend
from factory.secret.models import SecretLease, SecretRef
from factory.secret.redaction import REDACTED, contains_secret, redact

__all__ = [
    "REDACTED",
    "FakeSecretBackend",
    "SecretBroker",
    "SecretError",
    "SecretLease",
    "SecretRef",
    "contains_secret",
    "redact",
]
