"""Agent Zero module health — derived from adapter-tracked interaction history, never a live probe
this package performs on its own initiative (no ambient network access; see :mod:`policy`).
"""

from __future__ import annotations

from factory.integrations.agent_zero.models import ModuleHealth, ModuleHealthState

#: Consecutive-crash threshold after which the module is reported UNAVAILABLE, not just DEGRADED.
DEFAULT_UNAVAILABLE_AFTER_FAILURES = 3


def check_health(
    *,
    consecutive_failures: int,
    now: int,
    last_success_at: int | None = None,
    unavailable_after_failures: int = DEFAULT_UNAVAILABLE_AFTER_FAILURES,
) -> ModuleHealth:
    """Derive health from tracked interaction history (never assumed healthy by default)."""
    if last_success_at is None and consecutive_failures == 0:
        return ModuleHealth(
            ModuleHealthState.UNAVAILABLE, "no successful interaction recorded", now
        )
    if consecutive_failures >= unavailable_after_failures:
        return ModuleHealth(
            ModuleHealthState.UNAVAILABLE, f"{consecutive_failures} consecutive failures", now
        )
    if consecutive_failures > 0:
        return ModuleHealth(
            ModuleHealthState.DEGRADED, f"{consecutive_failures} consecutive failure(s)", now
        )
    return ModuleHealth(ModuleHealthState.HEALTHY, "recent interaction succeeded", now)
