"""Simulated three-workstream demonstration — IP-3 (preinstallation).

Wires the PH-6 engine end-to-end against the PH-4 router fake (route assignment) and the PH-5
sandbox fake (sandbox assignment): admit three *independent* workstreams (≤3 cap, a fourth is
denied), assign an isolated checkout + fake sandbox + fake route to each, drive each lane's
lifecycle, confirm no conflicts, and integrate through the coordinator that never edits source.
Fully deterministic and offline; live integration is LIVE_INTEGRATION_PENDING.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integration.coordinator import COORDINATOR_EDITS_SOURCE, IntegrationCoordinator
from factory.integration.models import WorkstreamResult
from factory.models.ollama_adapter import FakeOllamaAdapter
from factory.routing import (
    ApprovedRoster,
    ExecutionLedger,
    HealthLedger,
    ManualClock,
    ModelRouter,
    Provider,
    QuotaLimits,
    ResourceClass,
    ResourceProfile,
    RouteRequest,
    TaskType,
)
from factory.sandbox import FakeWslDockerBackend, ResourceLimits, SandboxSpec
from factory.scheduler import QuotaLedger, ResourceScheduler
from factory.workstream import AdmissionController, OwnershipRegistry, WorkstreamContract
from factory.workstream.conflict import ChangeManifest, ConflictDetector
from factory.workstream.lane import IsolatedCheckoutAssigner, Lane, LaneMachine, LaneState

_BASELINE = "baseline-commit-0"


@dataclass(frozen=True, slots=True)
class SimulatedIP3Report:
    admitted: tuple[str, ...]
    fourth_denied: bool
    checkouts_isolated: bool
    sandbox_ids: tuple[str, ...]
    routes: tuple[str, ...]
    conflicts: int
    integration_verdict: str
    promoted: tuple[str, ...]
    final_lane_states: tuple[str, ...]
    coordinator_edits_source: bool


def _contracts() -> tuple[WorkstreamContract, ...]:
    return tuple(
        WorkstreamContract(
            workstream_id=f"WS{i}",
            owner=f"owner-{i}",
            scope_paths=(f"src/mod{i}/**",),
            inputs=(),
            outputs=(f"mod{i}",),
            dependencies=(),
            owned_contracts=(f"CTR-{i}",),
            completion_gate=f"gate-{i}",
            baseline_commit=_BASELINE,
        )
        for i in (1, 2, 3)
    )


def _manifest(ws_id: str, index: int) -> ChangeManifest:
    return ChangeManifest(
        workstream_id=ws_id,
        files=frozenset({f"src/mod{index}/a.py"}),
        modules=frozenset({f"mod{index}"}),
    )


def run_simulated_ip3() -> SimulatedIP3Report:
    contracts = _contracts()
    admission = AdmissionController(max_active=3)
    ownership = OwnershipRegistry()
    checkouts = IsolatedCheckoutAssigner()
    lanes_machine = LaneMachine()
    sandbox = FakeWslDockerBackend()
    limits = ResourceLimits(1000, 2048, 4096, 128, 600)
    router = ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(100, 100_000, 100_000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: FakeOllamaAdapter()},
        clock=ManualClock(),
    )

    admitted: list[str] = []
    sandbox_ids: list[str] = []
    routes: list[str] = []
    lanes: list[Lane] = []

    for index, contract in enumerate(contracts, start=1):
        result = admission.admit(contract, list(contracts[: index - 1]), _BASELINE, frozenset())
        if not result.admitted:  # pragma: no cover - the three demo contracts are independent
            continue
        admitted.append(contract.workstream_id)
        ownership.acquire(f"src/mod{index}/a.py", contract.workstream_id)

        checkout_id = checkouts.assign(f"lane-{index}", "repo-main")
        handle = sandbox.provision(
            SandboxSpec(
                contract.workstream_id, contract.workstream_id, "img", "v1", resources=limits
            )
        )
        sandbox_ids.append(handle.sandbox_id)
        decision = router.route(
            RouteRequest(
                contract.workstream_id,
                "s1",
                TaskType.ROUTINE_CODING,
                ResourceProfile(ResourceClass.GPU_LIGHT, 1000, 1000, 1, 100),
            )
        )
        routes.append(decision.selected.route_key)

        lane = Lane(
            f"lane-{index}",
            contract.workstream_id,
            LaneState.PROPOSED,
            checkout_id,
            handle.sandbox_id,
            decision.selected.route_key,
        )
        for target in (
            LaneState.APPROVED,
            LaneState.READY,
            LaneState.ACTIVE,
            LaneState.VERIFICATION,
            LaneState.HANDOFF,
        ):
            lane = lanes_machine.transition(lane, target, cause="advance", actor="scheduler")
        lanes.append(lane)

    # A fourth workstream must be denied by the cap.
    fourth = WorkstreamContract(
        "WS4", "owner-4", ("src/mod4/**",), (), ("mod4",), (), ("CTR-4",), "gate-4", _BASELINE
    )
    fourth_denied = not admission.admit(fourth, list(contracts), _BASELINE, frozenset()).admitted

    manifests = [_manifest(ws, i) for i, ws in enumerate(admitted, start=1)]
    conflicts = ConflictDetector().detect(manifests)

    coordinator = IntegrationCoordinator()
    results = [
        WorkstreamResult(ws, True, _BASELINE, f"approved-{i}", manifests[i - 1])
        for i, ws in enumerate(admitted, start=1)
    ]
    report = coordinator.integrate(results)

    final_lanes = [
        lanes_machine.transition(
            lane, LaneState.INTEGRATED, cause="integrated", actor="coordinator"
        )
        for lane in lanes
    ]

    return SimulatedIP3Report(
        admitted=tuple(admitted),
        fourth_denied=fourth_denied,
        checkouts_isolated=checkouts.is_isolated(),
        sandbox_ids=tuple(sandbox_ids),
        routes=tuple(routes),
        conflicts=len(conflicts),
        integration_verdict=report.verdict.value,
        promoted=report.promoted,
        final_lane_states=tuple(lane.state.value for lane in final_lanes),
        coordinator_edits_source=COORDINATOR_EDITS_SOURCE,
    )
