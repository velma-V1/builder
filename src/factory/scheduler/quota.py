"""Quota and usage ledger (Task 4.4, ``01J §2.10`` budgets).

Deterministic per-scope accounting of requests, tokens, and wall time against versioned
:class:`QuotaLimits`. Admission is checked *before* a charge is applied so a call that would breach
a budget is refused rather than partially committed. State is snapshot/restore-able for restart
reconciliation.
"""

from __future__ import annotations

from collections.abc import Mapping

from factory.routing.errors import RoutingError
from factory.routing.models import QuotaLimits, UsageCounters


class QuotaLedger:
    """Per-scope usage accounting with fail-closed admission."""

    __slots__ = ("_default", "_limits", "_usage")

    def __init__(
        self,
        default_limits: QuotaLimits,
        per_scope_limits: Mapping[str, QuotaLimits] | None = None,
    ) -> None:
        self._default = default_limits
        self._limits: dict[str, QuotaLimits] = dict(per_scope_limits or {})
        self._usage: dict[str, UsageCounters] = {}

    def limits_for(self, scope: str) -> QuotaLimits:
        return self._limits.get(scope, self._default)

    def usage_for(self, scope: str) -> UsageCounters:
        return self._usage.get(scope, UsageCounters())

    def would_exceed(self, scope: str, *, requests: int, tokens: int, wall_time: int) -> bool:
        limits = self.limits_for(scope)
        projected = self.usage_for(scope).plus(
            requests=requests, tokens=tokens, wall_time=wall_time
        )
        return (
            projected.requests > limits.max_requests
            or projected.tokens > limits.max_tokens
            or projected.wall_time > limits.max_wall_time
        )

    def charge(self, scope: str, *, requests: int, tokens: int, wall_time: int) -> UsageCounters:
        """Apply a charge, or raise ``QUOTA_EXCEEDED`` without mutating state (fail-closed)."""
        if requests < 0 or tokens < 0 or wall_time < 0:
            raise RoutingError("QUOTA_NEGATIVE", "quota charge components must be non-negative")
        if self.would_exceed(scope, requests=requests, tokens=tokens, wall_time=wall_time):
            raise RoutingError("QUOTA_EXCEEDED", f"charge would exceed quota for scope {scope}")
        updated = self.usage_for(scope).plus(
            requests=requests, tokens=tokens, wall_time=wall_time
        )
        self._usage[scope] = updated
        return updated

    def remaining(self, scope: str) -> QuotaLimits:
        limits = self.limits_for(scope)
        used = self.usage_for(scope)
        return QuotaLimits(
            max_requests=max(0, limits.max_requests - used.requests),
            max_tokens=max(0, limits.max_tokens - used.tokens),
            max_wall_time=max(0, limits.max_wall_time - used.wall_time),
        )

    def snapshot(self) -> tuple[tuple[str, UsageCounters], ...]:
        return tuple(sorted(self._usage.items()))

    def restore(self, usage: tuple[tuple[str, UsageCounters], ...]) -> None:
        self._usage = dict(usage)
