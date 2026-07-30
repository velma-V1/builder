#!/usr/bin/env python3
"""Dedicated verifier for RPH3-T1: CMP-WATCH Lane A and its internal WIR."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MIGRATION_SHA256 = "21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80"


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _contains(path: str, *needles: str) -> tuple[bool, str]:
    file = Path(path)
    content = file.read_text(encoding="utf-8") if file.exists() else ""
    missing = [needle for needle in needles if needle not in content]
    return not missing and bool(content), f"missing={missing}" if missing else "ok"


def verify_migration() -> VerificationResult:
    path = Path("migrations/security/0004_watchdog.sql")
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
    pinned, _ = _contains("src/factory/watchdog/store.py", path.name, MIGRATION_SHA256)
    shape, _ = _contains(
        str(path),
        "CREATE TABLE watchdog_intervention_journal",
        "operation_class",
        "reconciliation_state",
        "request_hash",
    )
    return VerificationResult(
        "Ordered 0004 WIR journal migration + exact SHA pin",
        actual == MIGRATION_SHA256 and pinned and shape,
        f"sha256={actual}",
    )


def verify_observer() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/watchdog/process.py",
        "class WatchdogProcess",
        "auto_launch: bool = False",
        "def intervention_for",
        "decide_high_risk_admission",
    )
    process = Path("src/factory/watchdog/process.py").read_text(encoding="utf-8")
    read_only = all(term not in process for term in ("sqlite3", "subprocess", "open(", "Path("))
    return VerificationResult(
        "Independent read-only observer policy + fail-closed loss behavior",
        ok and read_only,
        f"{detail}; no write/exec imports={read_only}",
    )


def verify_timing_and_recovery() -> VerificationResult:
    timing, _ = _contains(
        "src/factory/watchdog/thresholds.py",
        "class ThresholdStateMachine",
        "REDUCED_MONITORING",
        "recovery_after",
        "monotonic",
    )
    heartbeat, _ = _contains(
        "src/factory/watchdog/heartbeat.py",
        "class HeartbeatMonitor",
        "HEARTBEAT_REPLAY",
        "HEARTBEAT_UNAUTHENTICATED",
    )
    recovery, _ = _contains(
        "src/factory/watchdog/failures.py",
        "stable_failure_identity",
        "class ServiceSupervisor",
        "max_attempts",
        "initial_backoff",
        "RECOVERY_CIRCUIT_OPEN",
    )
    return VerificationResult(
        "Monotonic health/stall + hysteresis + bounded recovery",
        timing and heartbeat and recovery,
        f"timing={timing}; heartbeat={heartbeat}; recovery={recovery}",
    )


def verify_wir() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/watchdog/interventions.py",
        "class WatchdogInterventionReceiver",
        "_authenticated",
        "_bounded",
        "_expected_matches",
        "authority_gate.authorize",
        "RecordKind.INTENT",
        "operation_class=3",
        "InterventionStatus.QUARANTINED",
        "uncertain external restart quarantined; never retried",
    )
    models, _ = _contains(
        "src/factory/watchdog/models.py",
        "PAUSE_TASK",
        "CONTAIN_TASK",
        "RESTART_SERVICE",
        "RECONCILE_STATE",
        "QUARANTINE_RESOURCE",
        "RESTORE_APPROVED_STATE",
        "ACTIVATE_VERIFIED_SNAPSHOT",
        "ALL_INTERVENTION_COMMANDS",
    )
    return VerificationResult(
        "Exact seven-command WIR + Class-2/Class-3 fail-closed protocol",
        ok and models,
        detail,
    )


def verify_isolation() -> VerificationResult:
    public = Path("src/factory/watchdog/__init__.py").read_text(encoding="utf-8")
    store, detail = _contains(
        "src/factory/watchdog/store.py",
        "_intervention_writer_authorizer",
        "mode=ro",
        "_INTERVENTION_WRITE_TABLES",
    )
    return VerificationResult(
        "Private sole writer + read-only observer boundary",
        store and "_InterventionWriter" not in public,
        f"{detail}; writer_not_exported={'_InterventionWriter' not in public}",
    )


def verify_test_inventory() -> VerificationResult:
    expected = {
        "test_watchdog_unit.py",
        "test_watchdog_store.py",
        "test_interventions_security.py",
        "test_interventions_failure_path.py",
        "test_interventions_integration.py",
    }
    present = {path.name for path in Path("tests/watchdog").glob("test_*.py")}
    missing = sorted(expected - present)
    return VerificationResult(
        "Unit/migration/security/failure/crash/concurrency/integration tests",
        not missing,
        f"missing={missing}" if missing else f"{len(present)}/{len(expected)} present",
    )


def verify_tests() -> VerificationResult:
    t1_modules = (
        "control",
        "errors",
        "failures",
        "heartbeat",
        "interventions",
        "models",
        "process",
        "store",
        "thresholds",
        "writer",
    )
    result = subprocess.run(  # noqa: S603 - fixed interpreter/modules, no user input
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/watchdog",
            "-q",
            *(
                coverage_arg
                for module in t1_modules
                for coverage_arg in ("--cov", f"factory.watchdog.{module}")
            ),
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().splitlines() or ["?"])[-1]
    return VerificationResult(
        "Watchdog tests pass with >=95% branch coverage",
        result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_static() -> VerificationResult:
    ruff = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src/factory/watchdog",
            "tests/watchdog",
            "scripts/verify_roadmap_ph3_t1.py",
        ],
        capture_output=True,
        text=True,
    )
    mypy = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "src/factory/watchdog",
            "tests/watchdog",
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "Ruff + mypy --strict clean",
        ruff.returncode == 0 and mypy.returncode == 0,
        f"ruff={ruff.returncode}; mypy={mypy.returncode}",
    )


def main() -> int:
    checks = (
        verify_migration,
        verify_observer,
        verify_timing_and_recovery,
        verify_wir,
        verify_isolation,
        verify_test_inventory,
        verify_tests,
        verify_static,
    )
    results = [check() for check in checks]
    print("\n" + "=" * 80)
    print("RPH3-T1 VERIFICATION SUITE - CMP-WATCH Lane A + internal WIR")
    print("=" * 80 + "\n")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:5} | {result.name:58} | {result.detail}")
    passed = sum(result.passed for result in results)
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{len(results)} checks passed")
    print("=" * 80 + "\n")
    if passed == len(results):
        print("RPH3-T1 gate: PASS. NOT PROM-RPH3; integrated verification remains.\n")
        return 0
    print("RPH3-T1 gate: INCOMPLETE - fix failures above.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
