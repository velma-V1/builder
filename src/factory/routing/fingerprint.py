"""Fingerprint sufficiency validation — CTR-MODEL-FINGERPRINT (``01J §3.1``).

A display name or mutable tag alone is never sufficient identity. :func:`require_full_fingerprint`
enforces that every material identity field is populated before a fingerprint may be attached to an
execution record; a fingerprint that carries only a declared name is rejected.
"""

from __future__ import annotations

from factory.routing.errors import RoutingError
from factory.routing.models import ModelFingerprint

# Material identity fields that a mutable tag cannot stand in for (``01J §3.1``).
_REQUIRED_TEXT_FIELDS = (
    "family",
    "declared_name",
    "artifact_digest",
    "quantization",
    "fmt",
    "runtime_version",
    "adapter_version",
    "routing_policy_version",
)


def require_full_fingerprint(fingerprint: ModelFingerprint) -> ModelFingerprint:
    """Return the fingerprint if complete, else raise ``FINGERPRINT_INSUFFICIENT``."""
    missing = [name for name in _REQUIRED_TEXT_FIELDS if not getattr(fingerprint, name).strip()]
    if fingerprint.context_window <= 0:
        missing.append("context_window")
    if not fingerprint.sampling:
        missing.append("sampling")
    if missing:
        raise RoutingError(
            "FINGERPRINT_INSUFFICIENT",
            f"mutable tag insufficient; missing identity fields: {sorted(missing)}",
        )
    return fingerprint
