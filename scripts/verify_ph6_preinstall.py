#!/usr/bin/env python3
"""Verification suite for PH-6 (Section 6) — Three Parallel Workstreams (simulated core).

Scoped gate for the PH-6 simulated workstream core: the workstream engine, lane lifecycle, conflict
detection, scheduler/quarantine, and the integration coordinator, demonstrated end-to-end against the
PH-4/PH-5 deterministic fakes (simulated IP-3). It is NOT a phase-promotion gate and makes NO
live-runtime claim: live sandbox/router assignment and live cross-workstream integration remain
LIVE_INTEGRATION_PENDING (see docs/verification/ph6-pending-live-gate-register.md).

Run under the project environment, e.g. ``.venv/bin/python scripts/verify_ph6_preinstall.py``.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _exists(*rel: str) -> tuple[bool, str]:
    missing = [p for p in rel if not (ROOT / p).exists()]
    return (not missing), ("ok" if not missing else f"missing={missing}")


def verify_owned_path_layout() -> VerificationResult:
    ok, detail = _exists(
        "src/factory/workstream/admission.py",
        "src/factory/workstream/ownership.py",
        "src/factory/workstream/lane/lifecycle.py",
        "src/factory/workstream/conflict/detector.py",
        "src/factory/workstream/scheduler/policy.py",
        "src/factory/integration/coordinator.py",
        "src/factory/integration/demo.py",
    )
    return VerificationResult("PH-6 modules live at their plan-assigned owner paths", ok, detail)


def verify_admission_cap_and_independence() -> VerificationResult:
    from factory.workstream import AdmissionController, AdmissionOutcome, WorkstreamContract

    def ws(i: int, scope: str, contracts: tuple[str, ...] = ()) -> WorkstreamContract:
        return WorkstreamContract(
            f"W{i}", "o", (scope,), (), (), (), contracts, "g", "base-0"
        )

    ctrl = AdmissionController(max_active=3)
    active = [ws(1, "src/a/**"), ws(2, "src/b/**"), ws(3, "src/c/**")]
    cap = ctrl.admit(ws(4, "src/d/**"), active, "base-0").outcome is AdmissionOutcome.DENIED_CAP
    overlap = not ctrl.admit(ws(5, "src/a/sub/**"), [ws(1, "src/a/**")], "base-0").admitted
    shared = not ctrl.admit(
        ws(6, "src/x/**", ("CTR-1",)), [ws(1, "src/a/**", ("CTR-1",))], "base-0"
    ).admitted
    independent = ctrl.admit(ws(7, "src/z/**"), [ws(1, "src/a/**")], "base-0").admitted
    ok = cap and overlap and shared and independent
    return VerificationResult(
        "Admission: <=3 cap + independence (not path-disjointness alone)", ok,
        f"cap={cap}; overlap_denied={overlap}; shared_denied={shared}; independent_ok={independent}",
    )


def verify_lane_lifecycle() -> VerificationResult:
    from factory.workstream import WorkstreamError
    from factory.workstream.lane import Lane, LaneMachine, LaneState

    machine = LaneMachine()
    lane = Lane("l1", "W1", LaneState.PROPOSED, "wt-1")
    legal = True
    for target in (LaneState.APPROVED, LaneState.READY, LaneState.ACTIVE):
        lane = machine.transition(lane, target, cause="c", actor="a")
    illegal = False
    try:
        machine.transition(
            Lane("l2", "W1", LaneState.PROPOSED, "wt-2"), LaneState.ACTIVE, cause="c", actor="a"
        )
    except WorkstreamError as exc:
        illegal = exc.code == "LANE_ILLEGAL_TRANSITION"
    inconsistent = False
    try:
        r = machine.transition(
            Lane("l3", "W1", LaneState.READY, "wt-3"), LaneState.ACTIVE, cause="c", actor="a",
            task_state="PAUSED",
        )
        _ = r
    except WorkstreamError as exc:
        inconsistent = exc.code == "LANE_TASK_INCONSISTENT"
    ok = legal and lane.state is LaneState.ACTIVE and illegal and inconsistent
    return VerificationResult(
        "Lane lifecycle: legal transitions + illegal/inconsistent fail closed", ok,
        f"illegal={illegal}; task_inconsistent={inconsistent}",
    )


def verify_conflict_and_baseline() -> VerificationResult:
    from factory.workstream import WorkstreamError
    from factory.workstream.conflict import BaselineTracker, ChangeManifest, ConflictDetector

    detector = ConflictDetector()
    conflict = bool(
        detector.detect([
            ChangeManifest("W1", symbols=frozenset({"foo"})),
            ChangeManifest("W2", symbols=frozenset({"foo"})),
        ])
    )
    independent = detector.is_independent([
        ChangeManifest("W1", files=frozenset({"a.py"})),
        ChangeManifest("W2", files=frozenset({"b.py"})),
    ])
    tracker = BaselineTracker()
    tracker.record("s1", "commit-a")
    drift = tracker.has_drifted("s1", "commit-b")
    immutable = False
    try:
        tracker.record("s1", "commit-b")
    except WorkstreamError as exc:
        immutable = exc.code == "BASELINE_IMMUTABLE"
    ok = conflict and independent and drift and immutable
    return VerificationResult(
        "Conflict detection beyond files + immutable baseline drift", ok,
        f"conflict={conflict}; independent={independent}; drift={drift}; immutable={immutable}",
    )


def verify_scheduler_quarantine() -> VerificationResult:
    from factory.workstream.scheduler import (
        FailureCounter,
        InterruptOutcome,
        WorkstreamScheduler,
        normalize_signature,
    )

    sig = normalize_signature(
        component="c", operation="o", phase="p", error_code="E", resource="r", root_cause="rc"
    )
    fc = FailureCounter()
    fc.record("W1", sig)
    fc.record("W1", sig)
    quarantined = fc.record("W1", sig)
    transient_excluded = True
    fc2 = FailureCounter()
    fc2.record("W2", sig)
    fc2.record("W2", sig, transient=True)
    fc2.record("W2", sig)
    transient_excluded = fc2.count("W2") == 2 and not fc2.is_quarantined("W2")
    sched = WorkstreamScheduler()
    checkpointed = sched.interrupt(
        requester_priority=9, holder_priority=1, non_preemptible=False,
        checkpoint_within_deadline=True,
    ) is InterruptOutcome.CHECKPOINTED_PAUSE
    ok = quarantined and transient_excluded and checkpointed
    return VerificationResult(
        "Scheduler: 3-failure quarantine + checkpointed interruption", ok,
        f"quarantined={quarantined}; transient_excluded={transient_excluded}; checkpointed={checkpointed}",
    )


def verify_coordinator_never_edits_source() -> VerificationResult:
    from factory.integration import (
        COORDINATOR_EDITS_SOURCE,
        IntegrationCoordinator,
        IntegrationVerdict,
        WorkstreamResult,
    )
    from factory.workstream.conflict import ChangeManifest

    coord = IntegrationCoordinator()
    report = coord.integrate([
        WorkstreamResult("W1", True, "base", "a1", ChangeManifest("W1", files=frozenset({"s.py"}))),
        WorkstreamResult("W2", True, "base", "a2", ChangeManifest("W2", files=frozenset({"s.py"}))),
    ])
    blocked = report.verdict is IntegrationVerdict.BLOCKED_CONFLICTS
    remediation = bool(report.remediation) and report.remediation[0].owning_workstream in {"W1", "W2"}
    ok = blocked and remediation and COORDINATOR_EDITS_SOURCE is False
    return VerificationResult(
        "Integration coordinator assigns remediation and never edits source", ok,
        f"blocked={blocked}; remediation={remediation}; edits_source={COORDINATOR_EDITS_SOURCE}",
    )


def verify_simulated_three_workstream_demo() -> VerificationResult:
    from factory.integration import run_simulated_ip3

    r = run_simulated_ip3()
    ok = (
        r.admitted == ("WS1", "WS2", "WS3")
        and r.fourth_denied
        and r.checkouts_isolated
        and len(set(r.sandbox_ids)) == 3
        and all(r.routes)
        and r.conflicts == 0
        and r.integration_verdict == "INTEGRATED"
        and set(r.final_lane_states) == {"INTEGRATED"}
        and r.coordinator_edits_source is False
    )
    return VerificationResult(
        "Simulated three-workstream demonstration (IP-3) integrates via fakes", ok,
        f"admitted={r.admitted}; fourth_denied={r.fourth_denied}; verdict={r.integration_verdict}",
    )


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/workstream", "tests/integration", "-q",
            "--cov=src/factory/workstream", "--cov=src/factory/integration",
            "--cov-branch", "--cov-fail-under=95",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "PH-6 tests pass with >=95% branch coverage", result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "src/factory/workstream", "src/factory/integration",
            "tests/workstream", "tests/integration",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("Ruff clean (PH-6 src + tests)", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy",
            "src/factory/workstream", "src/factory/integration",
            "tests/workstream", "tests/integration", "--strict",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("mypy --strict clean (PH-6)", result.returncode == 0, f"exit {result.returncode}")


def verify_evidence_present() -> VerificationResult:
    ok, detail = _exists(
        "docs/verification/ph6-preinstall-evidence.md",
        "docs/verification/ph6-requirement-to-test-matrix.md",
        "docs/verification/ph6-failure-path-matrix.md",
        "docs/verification/ph6-simulated-ip3-report.md",
        "docs/verification/ph6-pending-live-gate-register.md",
    )
    return VerificationResult("PH-6 evidence package present", ok, detail)


def main() -> int:
    verifications = [
        verify_owned_path_layout,
        verify_admission_cap_and_independence,
        verify_lane_lifecycle,
        verify_conflict_and_baseline,
        verify_scheduler_quarantine,
        verify_coordinator_never_edits_source,
        verify_simulated_three_workstream_demo,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
        verify_evidence_present,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("PH-6 SIMULATED VERIFICATION SUITE — Three Parallel Workstreams")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:64} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print("PH-6 simulated gate: PASS. LIVE_INTEGRATION_PENDING; not a phase promotion.\n")
        return 0
    print("PH-6 simulated gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
