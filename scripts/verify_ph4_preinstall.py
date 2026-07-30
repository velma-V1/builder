#!/usr/bin/env python3
"""Verification suite for PH-4 (Section 4) — Model & Coding-Tool Routing & Quotas (preinstallation).

Scoped gate for the PH-4 preinstallation routing core built against deterministic fake provider
adapters. It is NOT a phase-promotion gate and it makes NO live-runtime claim: wiring the live Ollama
runtime adapter and the live Aider worker adapter to real daemons remains LIVE_RUNTIME_PENDING
(see docs/verification/ph4-pending-live-gate-register.md).

Run under the project environment, e.g. ``.venv/bin/python scripts/verify_ph4_preinstall.py``.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# PH-4 owner paths per docs/plans/section-4-model-and-worker-routing.md.
SRC_PATHS = (
    "src/factory/routing",
    "src/factory/scheduler",
    "src/factory/models/ollama_adapter",
    "src/factory/workers/aider_adapter",
)
TEST_PATH = "tests/routing"


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _exists(*rel_paths: str) -> tuple[bool, str]:
    missing = [p for p in rel_paths if not (ROOT / p).exists()]
    return (not missing), ("ok" if not missing else f"missing={missing}")


def verify_owned_path_layout() -> VerificationResult:
    ok, detail = _exists(
        "src/factory/routing/router.py",
        "src/factory/routing/roster.py",
        "src/factory/routing/fingerprint.py",
        "src/factory/routing/records.py",
        "src/factory/routing/health.py",
        "src/factory/routing/adapters/base.py",
        "src/factory/scheduler/scheduler.py",
        "src/factory/scheduler/quota.py",
        "src/factory/models/ollama_adapter/fake_ollama.py",
        "src/factory/workers/aider_adapter/fake_aider.py",
    )
    return VerificationResult("PH-4 modules live at their plan-assigned owner paths", ok, detail)


def verify_roster_excludes_glm() -> VerificationResult:
    from factory.routing.models import TaskType
    from factory.routing.roster import EXCLUDED_MODEL_IDS, ApprovedRoster

    roster = ApprovedRoster.activate()
    # The default roster defines a route for every TaskType member (roster._ROUTES is complete).
    approved: list[str] = []
    for task_type in TaskType:
        approved.extend(roster.descriptor(k).model_id.lower() for k in roster.candidates_for(task_type))
    leaked = [m for m in approved if "glm" in m]
    excluded_present = "glm-4.7" in EXCLUDED_MODEL_IDS and "zai-glm-4.7" in EXCLUDED_MODEL_IDS
    ok = not leaked and excluded_present
    detail = f"leaked={leaked}; exclusion_constant={excluded_present}"
    return VerificationResult("No GLM route is approved (03 §6); exclusion constant present", ok, detail)


def verify_provider_adapter_interface() -> VerificationResult:
    from factory.models.ollama_adapter import FakeOllamaAdapter
    from factory.routing.adapters import ProviderAdapter
    from factory.workers.aider_adapter import FakeAiderWorker

    ok = isinstance(FakeOllamaAdapter(), ProviderAdapter) and isinstance(
        FakeAiderWorker(), ProviderAdapter
    )
    return VerificationResult("Both fakes implement the ProviderAdapter interface", ok, f"ok={ok}")


def verify_no_silent_substitution() -> VerificationResult:
    """A failing route is recorded on the SAME route; a substitute must be explicit + approved."""
    from factory.models.ollama_adapter import FakeOllamaAdapter
    from factory.routing import (
        ApprovedRoster,
        ExecutionLedger,
        ExecutionStatus,
        HealthLedger,
        ManualClock,
        ModelRouter,
        Provider,
        QuotaLimits,
        ResourceClass,
        ResourceProfile,
        RouteRequest,
        RuntimeStatus,
        TaskType,
    )
    from factory.routing.errors import RoutingError
    from factory.scheduler import QuotaLedger, ResourceScheduler

    router = ModelRouter(
        roster=ApprovedRoster.activate(),
        scheduler=ResourceScheduler(),
        quota=QuotaLedger(QuotaLimits(100, 100000, 100000)),
        ledger=ExecutionLedger(),
        health=HealthLedger(),
        adapters={Provider.OLLAMA: FakeOllamaAdapter(status=RuntimeStatus.UNAVAILABLE)},
        clock=ManualClock(),
    )
    req = RouteRequest("t", "s", TaskType.DISPATCH, ResourceProfile(ResourceClass.GPU_LIGHT, 1, 1, 1, 1))
    out = router.execute(req)
    same_route = out.record is not None and out.record.route_key == "OLLAMA:qwen3:8b"
    explicit = out.record is not None and out.record.status is ExecutionStatus.RUNTIME_UNAVAILABLE
    no_auto_fallback = not router.fallbacks()
    try:
        router.fallback(out.record.record_id, req, "OLLAMA:ghost")  # type: ignore[union-attr]
        rejected = False
    except RoutingError as exc:
        rejected = exc.code == "FALLBACK_UNAPPROVED"
    ok = same_route and explicit and no_auto_fallback and rejected
    return VerificationResult(
        "No silent substitution: explicit unavailable + approved-only fallback", ok,
        f"same_route={same_route}; explicit={explicit}; no_auto={no_auto_fallback}; rejected={rejected}",
    )


def verify_fingerprint_and_append_only() -> VerificationResult:
    from factory.routing import (
        ExecutionLedger,
        ExecutionRecord,
        ExecutionStatus,
        require_full_fingerprint,
    )
    from factory.routing.errors import RoutingError
    from factory.routing.models import ModelFingerprint

    bare = ModelFingerprint(
        "f", "n", "", "q", "fmt", "ov", "rv", 8, 4, (("t", "0"),), "s", "ts", "ad", "rp", "g"
    )
    try:
        require_full_fingerprint(bare)
        fp_rejected = False
    except RoutingError as exc:
        fp_rejected = exc.code == "FINGERPRINT_INSUFFICIENT"

    ledger = ExecutionLedger()
    rec = ExecutionRecord("e1", "t", "s", 1, "OLLAMA:qwen3:8b", "d", ExecutionStatus.SUCCEEDED, 0, "ok")
    ledger.record(rec)
    try:
        ledger.record(rec)
        append_only = False
    except RoutingError as exc:
        append_only = exc.code == "RECORD_DUPLICATE"
    ok = fp_rejected and append_only
    return VerificationResult(
        "Bare tag rejected (01J §3.1); execution ledger is append-only", ok,
        f"fp_rejected={fp_rejected}; append_only={append_only}",
    )


def verify_single_gpu_heavy_and_reservations() -> VerificationResult:
    from factory.routing import ResourceClass, ResourceProfile
    from factory.scheduler import AdmissionOutcome, ResourceScheduler

    sched = ResourceScheduler()
    heavy = ResourceProfile(ResourceClass.GPU_HEAVY, 4000, 4000, 1, 100)
    first = sched.admit("t1", "AIDER:aider", heavy, now=0)
    second = sched.admit("t2", "OLLAMA:qwen3:14b", heavy, now=0)
    ok = first.admitted and second.outcome is AdmissionOutcome.DENIED_GPU_HEAVY_BUSY
    return VerificationResult("Single-active GPU-heavy reservation policy enforced", ok, f"ok={ok}")


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/routing", "-q",
            "--cov=src/factory/routing",
            "--cov=src/factory/scheduler",
            "--cov=src/factory/models/ollama_adapter",
            "--cov=src/factory/workers/aider_adapter",
            "--cov-branch", "--cov-fail-under=95",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "PH-4 tests pass with >=95% branch coverage", result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "src/factory/routing", "src/factory/scheduler",
            "src/factory/models/ollama_adapter", "src/factory/workers/aider_adapter",
            "tests/routing",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("Ruff clean (PH-4 src + tests)", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy",
            "src/factory/routing", "src/factory/scheduler",
            "src/factory/models/ollama_adapter", "src/factory/workers/aider_adapter",
            "tests/routing", "--strict",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("mypy --strict clean (PH-4)", result.returncode == 0, f"exit {result.returncode}")


def verify_evidence_present() -> VerificationResult:
    ok, detail = _exists(
        "docs/verification/ph4-preinstall-evidence.md",
        "docs/verification/ph4-requirement-to-test-matrix.md",
        "docs/verification/ph4-failure-path-matrix.md",
        "docs/verification/ph4-pending-live-gate-register.md",
    )
    return VerificationResult("PH-4 evidence package present", ok, detail)


def main() -> int:
    verifications = [
        verify_owned_path_layout,
        verify_roster_excludes_glm,
        verify_provider_adapter_interface,
        verify_no_silent_substitution,
        verify_fingerprint_and_append_only,
        verify_single_gpu_heavy_and_reservations,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
        verify_evidence_present,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("PH-4 PREINSTALLATION VERIFICATION SUITE — Model & Coding-Tool Routing & Quotas")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:62} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print("PH-4 preinstallation gate: PASS. LIVE_RUNTIME_PENDING; not a phase promotion.\n")
        return 0
    print("PH-4 preinstallation gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
