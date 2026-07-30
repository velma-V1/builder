"""Deterministic model router (Tasks 4.3/4.5, ``01J §2/§5``, ``03 §7/§9``).

The router is the visible, operator-overridable authority that turns a declared task into an
approved route, an admitted reservation, a charged quota, an adapter call, and an append-only
execution record. Its non-negotiable invariants:

* **Deterministic + visible** — selection follows the ``03 §7`` roster order and always exposes the
  selected route and a human reason (``01J §5.1``).
* **Privacy before speed** — a ``LOCAL_ONLY`` task can never select a hosted route (``03 §9``);
  hosted routes need an explicit task-scoped ``CLOUD_ALLOWED`` grant.
* **No silent substitution** — :meth:`execute` never swaps the model. A different model is only ever
  reached through :meth:`fallback`, which closes the failed attempt, records a disclosed
  :class:`FallbackRecord`, opens a *new* execution record, and flags reverification (``01J §3.2``).
* **Explicit unavailability** — a runtime being down is a ``RUNTIME_UNAVAILABLE`` outcome, and an
  over-committed reservation is a denied :class:`AdmissionResult`; neither silently reroutes.
* **Restart reconciliation** — :meth:`reconcile_restart` rebuilds scheduler/quota state from a
  durable snapshot and surfaces in-flight records for bounded resume (``01J §2.7``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from factory.routing.adapters.base import CallRequest, CallResult, ProviderAdapter
from factory.routing.errors import RoutingError
from factory.routing.fingerprint import require_full_fingerprint
from factory.routing.health import HealthContext, HealthLedger, health_check_required
from factory.routing.models import (
    ExecutionRecord,
    ExecutionStatus,
    FallbackRecord,
    ModelDescriptor,
    Privacy,
    Provider,
    ResourceProfile,
    RouteDecision,
    RoutingSnapshot,
    TaskType,
)
from factory.routing.records import ExecutionLedger
from factory.routing.roster import ApprovedRoster
from factory.scheduler import AdmissionResult, QuotaLedger, ResourceScheduler


class ManualClock:
    """Deterministic monotonic clock for tests and reproducible records."""

    __slots__ = ("_now",)

    def __init__(self, start: int = 0) -> None:
        self._now = start

    def now(self) -> int:
        return self._now

    def advance(self, ticks: int = 1) -> int:
        if ticks < 0:
            raise RoutingError("CLOCK_BACKWARD", "clock may not move backward")
        self._now += ticks
        return self._now


@dataclass(frozen=True, slots=True)
class RouteRequest:
    task_id: str
    stage_id: str
    task_type: TaskType
    profile: ResourceProfile
    privacy: Privacy = Privacy.LOCAL_ONLY
    operator_override: str | None = None
    health_context: HealthContext = field(default_factory=HealthContext)
    prompt: str = ""
    max_tokens: int = 256
    timeout: int = 30
    quota_scope: str = "default"


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    decision: RouteDecision
    admission: AdmissionResult
    record: ExecutionRecord | None
    call: CallResult | None
    reverification_required: bool = False


class ModelRouter:
    """Central routing + execution authority over the approved roster."""

    __slots__ = (
        "_adapters", "_clock", "_health", "_ledger", "_quota", "_roster", "_scheduler", "_seq",
    )

    def __init__(
        self,
        roster: ApprovedRoster,
        scheduler: ResourceScheduler,
        quota: QuotaLedger,
        ledger: ExecutionLedger,
        health: HealthLedger,
        adapters: Mapping[Provider, ProviderAdapter],
        clock: ManualClock,
    ) -> None:
        self._roster = roster
        self._scheduler = scheduler
        self._quota = quota
        self._ledger = ledger
        self._health = health
        self._adapters = dict(adapters)
        self._clock = clock
        self._seq = 0

    # -- selection ---------------------------------------------------------------------------
    def _privacy_ok(self, descriptor: ModelDescriptor, privacy: Privacy) -> bool:
        return descriptor.is_local or privacy is Privacy.CLOUD_ALLOWED

    def route(self, request: RouteRequest) -> RouteDecision:
        """Deterministic, visible selection with an explicit reason (``01J §5.1/§5.2``)."""
        candidates = self._roster.candidates_for(request.task_type)

        if request.operator_override is not None:
            override = request.operator_override
            if not self._roster.is_approved(override):
                raise RoutingError("OVERRIDE_UNAPPROVED", f"override {override} is not approved")
            descriptor = self._roster.descriptor(override)
            if not self._privacy_ok(descriptor, request.privacy):
                raise RoutingError(
                    "OVERRIDE_PRIVACY", f"override {override} violates LOCAL_ONLY privacy"
                )
            reason = f"operator override -> {override}"
            selected, is_override = descriptor, True
        else:
            selected, is_override = self._select(candidates, request.privacy)
            reason = (
                f"deterministic roster selection for {request.task_type.value}"
                f" -> {selected.route_key}"
            )

        need_health = health_check_required(
            request.task_type,
            request.health_context,
            self._health.latest(selected.route_key),
            self._clock.now(),
        )
        return RouteDecision(
            task_id=request.task_id,
            task_type=request.task_type,
            selected=selected,
            reason=reason,
            privacy=request.privacy,
            operator_override=is_override,
            candidates=candidates,
            health_check_required=need_health,
        )

    def _select(
        self, candidates: tuple[str, ...], privacy: Privacy
    ) -> tuple[ModelDescriptor, bool]:
        for route_key in candidates:
            descriptor = self._roster.descriptor(route_key)
            if self._privacy_ok(descriptor, privacy):
                return descriptor, False
        raise RoutingError(
            "NO_APPROVED_ROUTE",
            "no approved route satisfies the privacy policy (hosted needs CLOUD_ALLOWED)",
        )

    # -- execution ---------------------------------------------------------------------------
    def _new_record_id(self) -> str:
        self._seq += 1
        return f"exec-{self._seq}"

    def _adapter_for(self, descriptor: ModelDescriptor) -> ProviderAdapter:
        try:
            return self._adapters[descriptor.provider]
        except KeyError:
            raise RoutingError(
                "ADAPTER_MISSING", f"no adapter registered for {descriptor.provider.value}"
            ) from None

    def execute(self, request: RouteRequest) -> ExecutionOutcome:
        """Route, admit, charge, and call — never substituting the selected model."""
        decision = self.route(request)
        descriptor = decision.selected
        now = self._clock.now()

        admission = self._scheduler.admit(
            request.task_id, descriptor.route_key, request.profile, now
        )
        if not admission.admitted:
            return ExecutionOutcome(decision, admission, None, None)

        assert admission.reservation is not None  # admitted implies a reservation
        reservation = admission.reservation
        adapter = self._adapter_for(descriptor)
        call = adapter.call(
            CallRequest(
                task_id=request.task_id,
                stage_id=request.stage_id,
                route_key=descriptor.route_key,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                timeout=request.timeout,
            )
        )
        if call.ok and call.fingerprint is not None:
            require_full_fingerprint(call.fingerprint)
        if call.ok:
            self._quota.charge(
                request.quota_scope, requests=1, tokens=call.tokens, wall_time=1
            )

        record = self._ledger.record(
            ExecutionRecord(
                record_id=self._new_record_id(),
                task_id=request.task_id,
                stage_id=request.stage_id,
                attempt=self._ledger.next_attempt(request.task_id, request.stage_id),
                route_key=descriptor.route_key,
                fingerprint_digest=call.fingerprint.digest() if call.fingerprint else "",
                status=call.status,
                started_at=now,
                reason=call.reason,
                error_code=call.error_code,
            )
        )
        self._scheduler.release(reservation.reservation_id, self._clock.now())
        return ExecutionOutcome(decision, admission, record, call)

    def fallback(
        self, failed_record_id: str, request: RouteRequest, substitute_route_key: str
    ) -> ExecutionOutcome:
        """Disclosed, reverified substitution after a failure (``01J §3.2``, ``§2.14/§2.15``)."""
        failed = self._ledger.get(failed_record_id)
        if failed is None:
            raise RoutingError("FALLBACK_UNKNOWN", f"no record {failed_record_id}")
        if failed.status not in {
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
            ExecutionStatus.RUNTIME_UNAVAILABLE,
        }:
            raise RoutingError(
                "FALLBACK_NOT_FAILED", f"record {failed_record_id} did not fail; no fallback"
            )
        if not self._roster.is_approved(substitute_route_key):
            raise RoutingError(
                "FALLBACK_UNAPPROVED", f"substitute {substitute_route_key} is not approved"
            )
        descriptor = self._roster.descriptor(substitute_route_key)
        if not self._privacy_ok(descriptor, request.privacy):
            raise RoutingError(
                "FALLBACK_PRIVACY", f"substitute {substitute_route_key} violates privacy"
            )

        now = self._clock.now()
        admission = self._scheduler.admit(
            request.task_id, substitute_route_key, request.profile, now
        )
        if not admission.admitted:
            return ExecutionOutcome(self.route(request), admission, None, None, True)

        assert admission.reservation is not None
        adapter = self._adapter_for(descriptor)
        call = adapter.call(
            CallRequest(
                task_id=request.task_id,
                stage_id=request.stage_id,
                route_key=substitute_route_key,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                timeout=request.timeout,
            )
        )
        if call.ok and call.fingerprint is not None:
            require_full_fingerprint(call.fingerprint)
        # New execution record supersedes the failed one; reverification is mandatory.
        record = self._ledger.record(
            ExecutionRecord(
                record_id=self._new_record_id(),
                task_id=request.task_id,
                stage_id=request.stage_id,
                attempt=self._ledger.next_attempt(request.task_id, request.stage_id),
                route_key=substitute_route_key,
                fingerprint_digest=call.fingerprint.digest() if call.fingerprint else "",
                status=call.status,
                started_at=now,
                reason=f"fallback from {failed.route_key}: {call.reason}",
                supersedes=failed_record_id,
                reverification_required=True,
            )
        )
        self._ledger.register_fallback(
            FallbackRecord(
                from_record_id=failed_record_id,
                to_record_id=record.record_id,
                reason=f"{failed.status.value} on {failed.route_key}",
                failed_fingerprint_digest=failed.fingerprint_digest,
                substitute_fingerprint_digest=record.fingerprint_digest,
                reverification_gates=("stage_reverify", "affected_gates"),
            )
        )
        self._scheduler.release(admission.reservation.reservation_id, self._clock.now())
        decision = RouteDecision(
            task_id=request.task_id,
            task_type=request.task_type,
            selected=descriptor,
            reason=f"fallback -> {substitute_route_key}",
            privacy=request.privacy,
            operator_override=False,
            candidates=(substitute_route_key,),
            health_check_required=True,
        )
        return ExecutionOutcome(decision, admission, record, call, True)

    # -- introspection -----------------------------------------------------------------------
    def fallbacks(self) -> tuple[FallbackRecord, ...]:
        """The disclosed substitution records (operator-visible provenance)."""
        return self._ledger.fallbacks()

    # -- durability --------------------------------------------------------------------------
    def snapshot(self) -> RoutingSnapshot:
        return RoutingSnapshot(
            reservations=self._scheduler.active(),
            records=self._ledger.all_records(),
            usage=self._quota.snapshot(),
        )

    def reconcile_restart(self, snapshot: RoutingSnapshot) -> tuple[ExecutionRecord, ...]:
        """Rebuild scheduler/quota from a durable snapshot; return in-flight records to resume."""
        self._scheduler.reconcile(snapshot.reservations, self._clock.now())
        self._quota.restore(snapshot.usage)
        return tuple(r for r in snapshot.records if r.status is ExecutionStatus.RUNNING)
