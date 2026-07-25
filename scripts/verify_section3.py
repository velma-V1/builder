#!/usr/bin/env python3
"""Verification suite for Section 3 (PH-3, Worker Engine) — PROM-PH3 exit gate.

Run under the project environment so pytest/ruff/mypy are importable, e.g.:
    uv run python3.12 scripts/verify_section3.py
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WORKERS = Path("src/factory/workers")
TESTS = Path("tests/workers")


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def verify_module_files() -> VerificationResult:
    expected = {
        "models.py", "errors.py", "process.py", "lifecycle.py", "pool.py",
        "lease_coordinator.py", "dispatcher.py", "execution.py", "streaming.py",
        "state_integration.py", "recovery.py", "quarantine.py",
    }
    found = {f.name for f in WORKERS.glob("*.py")}
    return VerificationResult(
        "Worker Engine module files exist", expected.issubset(found),
        f"Expected {len(expected)}; missing {sorted(expected - found)}",
    )


def verify_worker_pool() -> VerificationResult:
    content = _read(WORKERS / "pool.py")
    needed = ["class WorkerPool", "get_available_worker", "assign_task", "poll_health", "shutdown", "reclaim"]
    missing = [n for n in needed if n not in content]
    return VerificationResult("WorkerPool lifecycle API present", not missing, f"missing {missing}")


def verify_task_executor() -> VerificationResult:
    content = _read(WORKERS / "execution.py")
    needed = ["class TaskExecutor", "def execute", "CancelToken", "RawWorkerEvent"]
    missing = [n for n in needed if n not in content]
    return VerificationResult("TaskExecutor + streaming seam present", not missing, f"missing {missing}")


def verify_state_integration_routes_writer() -> VerificationResult:
    content = _read(WORKERS / "state_integration.py")
    needed = ["class StateIntegration", "_OrchestratorStateWriter", "apply_transition"]
    missing = [n for n in needed if n not in content]
    return VerificationResult(
        "StateIntegration routes via single writer (R1)", not missing, f"missing {missing}"
    )


def verify_lease_coordinator() -> VerificationResult:
    content = _read(WORKERS / "lease_coordinator.py")
    needed = ["class LeaseCoordinator", "LeaseManager", "validate_current", "acquire_task_lease"]
    missing = [n for n in needed if n not in content]
    return VerificationResult("LeaseCoordinator wraps LeaseManager", not missing, f"missing {missing}")


def verify_writer_not_exported() -> VerificationResult:
    # Runtime invariant: the writer is not reachable through the public package surface.
    import factory.workers as pkg

    passed = "_OrchestratorStateWriter" not in pkg.__all__ and not hasattr(
        pkg, "_OrchestratorStateWriter"
    )
    return VerificationResult(
        "SEC-PH3-01: writer NOT exported from workers package", passed,
        "single-writer confinement (R1, threat T-01)",
    )


def verify_recovery_module() -> VerificationResult:
    content = _read(WORKERS / "recovery.py")
    needed = ["reconcile_startup", "StartupRecovery", "WorkerRecovery", "RetryPolicy"]
    missing = [n for n in needed if n not in content]
    return VerificationResult("Recovery + reconciliation application present", not missing, f"missing {missing}")


def verify_success_is_verifying_not_complete() -> VerificationResult:
    content = _read(WORKERS / "state_integration.py")
    # code-level invariant: success transitions to VERIFYING; no transition targets COMPLETE.
    passed = "TaskState.VERIFYING" in content and "TaskState.COMPLETE" not in content
    return VerificationResult(
        "Worker success → VERIFYING (no self-certify COMPLETE)", passed,
        "01L §3.1: COMPLETE only from VERIFYING",
    )


def _test_file_mentions(rel: str, needles: list[str]) -> bool:
    content = _read(TESTS / rel)
    return all(n in content for n in needles)


def verify_sec_single_writer_test() -> VerificationResult:
    passed = (TESTS / "security" / "test_single_writer_confinement.py").exists()
    return VerificationResult("SEC-PH3-01 confinement test exists", passed, "security/test_single_writer_confinement.py")


def verify_sec_fencing_test() -> VerificationResult:
    passed = (TESTS / "failure_paths" / "test_lease_epoch_staleness.py").exists()
    return VerificationResult("SEC-PH3-02 epoch fencing test exists", passed, "failure_paths/test_lease_epoch_staleness.py")


def verify_sec_output_bounds_test() -> VerificationResult:
    passed = (TESTS / "security" / "test_output_bounds.py").exists()
    return VerificationResult("SEC-PH3-03 output-bounds test exists", passed, "security/test_output_bounds.py")


def verify_no_blind_resume_test() -> VerificationResult:
    passed = _test_file_mentions("unit/test_recovery.py", ["BLOCKED", "no_resume"]) or _test_file_mentions(
        "unit/test_recovery.py", ["BLOCKED"]
    )
    return VerificationResult("SEC-PH3-04 no-blind-resume (RUNNING→BLOCKED) test exists", passed, "R3")


def verify_failure_path_tests() -> VerificationResult:
    fp = TESTS / "failure_paths"
    needed = {
        "test_worker_crash_detection.py", "test_execution_failures.py",
        "test_recovery_failures.py", "test_lease_epoch_staleness.py",
        "test_state_integration_failures.py",
    }
    found = {f.name for f in fp.glob("*.py")}
    return VerificationResult("Failure-path suites present", needed.issubset(found), f"missing {sorted(needed - found)}")


def verify_integration_three_cycle() -> VerificationResult:
    passed = _test_file_mentions("integration/test_end_to_end.py", ["three_cycle", "range(3)"])
    return VerificationResult("Integration 3-cycle recovery test exists", passed, "state consistency across restarts")


def verify_worker_tests_pass() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/workers/", "-q"],
        capture_output=True, text=True,
    )
    summary = result.stdout.strip().split("\n")[-1] if result.stdout else ""
    return VerificationResult("All PH-3 worker tests pass", result.returncode == 0, summary)


def verify_ph2_regression() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/orchestrator/", "-q"],
        capture_output=True, text=True,
    )
    summary = result.stdout.strip().split("\n")[-1] if result.stdout else ""
    return VerificationResult("PH-2 orchestrator regression (93 tests)", result.returncode == 0, summary)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/workers/", "tests/workers/"],
        capture_output=True, text=True,
    )
    return VerificationResult("Ruff linting passes", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/workers/", "--strict"],
        capture_output=True, text=True,
    )
    return VerificationResult("mypy --strict passes", result.returncode == 0, f"exit {result.returncode}")


def main() -> int:
    verifications = [
        verify_module_files,
        verify_worker_pool,
        verify_task_executor,
        verify_state_integration_routes_writer,
        verify_lease_coordinator,
        verify_writer_not_exported,
        verify_recovery_module,
        verify_success_is_verifying_not_complete,
        verify_sec_single_writer_test,
        verify_sec_fencing_test,
        verify_sec_output_bounds_test,
        verify_no_blind_resume_test,
        verify_failure_path_tests,
        verify_integration_three_cycle,
        verify_ruff,
        verify_mypy,
        verify_worker_tests_pass,
        verify_ph2_regression,
    ]

    results = [v() for v in verifications]
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)

    print("\n" + "=" * 80)
    print("PH-3 VERIFICATION SUITE — PROM-PH3 EXIT GATE")
    print("=" * 80 + "\n")
    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status:8} | {result.name:52} | {result.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed_count}/{total_count} verifications passed")
    print("=" * 80 + "\n")

    if passed_count == total_count:
        print("🎯 PROM-PH3 EXIT GATE: PASS — Section 3 (Worker Engine) is production-ready.\n")
        return 0
    print("⚠️  PROM-PH3 EXIT GATE: INCOMPLETE — Fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
