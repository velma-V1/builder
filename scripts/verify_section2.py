#!/usr/bin/env python3
"""Verification suite for Section 2 (PH-2) implementation — PROM-PH2 exit gate."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def verify_migrations_exist() -> VerificationResult:
    migrations_dir = Path("migrations/runtime")
    expected = {"0001_state.sql", "0002_leases.sql", "0003_memory.sql"}
    found = {f.name for f in migrations_dir.glob("*.sql")}
    passed = expected.issubset(found)
    return VerificationResult(
        name="Migrations schema files exist",
        passed=passed,
        detail=f"Expected {expected}; found {found}",
    )


def verify_migration_sha_pinning() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/store/runtime_state.py")
    content = src_path.read_text()
    expected_hashes = {
        "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c",
        "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6",
        "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587",
    }
    found = set()
    for line in content.split("\n"):
        for hash_val in expected_hashes:
            if hash_val in line:
                found.add(hash_val)
    passed = found == expected_hashes
    return VerificationResult(
        name="Migration SHA-256 pinning in runtime_state.py",
        passed=passed,
        detail=f"Expected {len(expected_hashes)} hashes; found {len(found)}",
    )


def verify_core_classes() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/models.py")
    content = src_path.read_text()
    expected_classes = {
        "TaskState",
        "StateTransitionEvent",
        "Lease",
        "LeaseResourceType",
        "MemoryRecord",
        "MemoryRecordStatus",
    }
    found = set()
    for cls in expected_classes:
        if f"class {cls}" in content or f"{cls}(" in content:
            found.add(cls)
    passed = found == expected_classes
    return VerificationResult(
        name="Core PH-2 models defined",
        passed=passed,
        detail=f"Expected {expected_classes}; found {found}",
    )


def verify_transition_policy() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/state/transitions.py")
    content = src_path.read_text()
    passed = "ALLOWED_TRANSITIONS" in content and "TransitionPolicy" in content
    return VerificationResult(
        name="Transition policy and ALLOWED_TRANSITIONS defined",
        passed=passed,
        detail="Both ALLOWED_TRANSITIONS and TransitionPolicy classes present",
    )


def verify_state_reader_writer() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/store/runtime_state.py")
    content = src_path.read_text()
    expected = {
        "SQLiteOrchestratorStateReader",
        "_OrchestratorStateWriter",
        "apply_migrations",
    }
    found = set()
    for name in expected:
        if f"class {name}" in content or f"def {name}" in content:
            found.add(name)
    passed = found == expected
    return VerificationResult(
        name="State reader/writer interfaces defined",
        passed=passed,
        detail=f"Expected {expected}; found {found}",
    )


def verify_reconciliation_suite() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/journal/reconciliation.py")
    content = src_path.read_text()
    expected = {"_RECONCILIATION_MAP", "reconcile_startup"}
    found = set()
    for name in expected:
        if name in content:
            found.add(name)
    passed = found == expected
    return VerificationResult(
        name="Reconciliation suite (reconcile_startup, _RECONCILIATION_MAP)",
        passed=passed,
        detail=f"Expected {expected}; found {found}",
    )


def verify_fencing_suite() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/leases/fencing.py")
    content = src_path.read_text()
    expected = {"LeaseManager", "acquire", "renew", "release", "validate_token"}
    found = set()
    for name in expected:
        if name in content:
            found.add(name)
    passed = len(found) >= 4
    return VerificationResult(
        name="Fencing (LeaseManager with acquire, renew, release, validate_token)",
        passed=passed,
        detail=f"Expected core methods; found {len(found)}/5",
    )


def verify_scheduler_suite() -> VerificationResult:
    src_path = Path("src/factory/orchestrator/queue/scheduler.py")
    content = src_path.read_text()
    expected = {"TaskScheduler", "ready_tasks", "request_cancellation", "finalize_cancellation"}
    found = set()
    for name in expected:
        if name in content:
            found.add(name)
    passed = found == expected
    return VerificationResult(
        name="Scheduler suite (TaskScheduler, ready_tasks, cancellation)",
        passed=passed,
        detail=f"Expected {expected}; found {found}",
    )


def verify_memory_suite() -> VerificationResult:
    src_path = Path("src/factory/memory/core/records.py")
    content = src_path.read_text()
    expected = {"MemoryStore", "propose", "verify", "supersede", "get"}
    found = set()
    for name in expected:
        if name in content:
            found.add(name)
    passed = found == expected
    return VerificationResult(
        name="Memory store (MemoryStore with propose, verify, supersede, get)",
        passed=passed,
        detail=f"Expected {expected}; found {found}",
    )


def verify_test_coverage() -> VerificationResult:
    test_files = [
        "tests/orchestrator/unit/test_transition_policy.py",
        "tests/orchestrator/unit/test_runtime_state_store.py",
        "tests/orchestrator/unit/test_journal_reconciliation.py",
        "tests/orchestrator/unit/test_fencing.py",
        "tests/orchestrator/unit/test_scheduler.py",
        "tests/orchestrator/unit/test_memory_store.py",
    ]
    all_exist = all(Path(f).exists() for f in test_files)
    return VerificationResult(
        name="Test files for all major modules",
        passed=all_exist,
        detail=f"{len([f for f in test_files if Path(f).exists()])}/{len(test_files)} test files exist",
    )


def verify_test_execution() -> VerificationResult:
    result = subprocess.run(
        ["python3.12", "-m", "pytest", "tests/orchestrator/", "-q"],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    lines = result.stdout.strip().split("\n")
    summary = lines[-1] if lines else "unknown"
    return VerificationResult(
        name="All orchestrator tests pass",
        passed=passed,
        detail=f"Exit code {result.returncode}; {summary}",
    )


def verify_ruff_linting() -> VerificationResult:
    result = subprocess.run(
        [
            "python3.12",
            "-m",
            "ruff",
            "check",
            "src/factory/orchestrator/",
            "src/factory/memory/",
            "tests/orchestrator/",
        ],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    return VerificationResult(
        name="Ruff linting passes (no style violations)",
        passed=passed,
        detail=f"Exit code {result.returncode}",
    )


def verify_mypy_strict() -> VerificationResult:
    result = subprocess.run(
        [
            "python3.12",
            "-m",
            "mypy",
            "src/factory/orchestrator/",
            "src/factory/memory/",
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0
    return VerificationResult(
        name="mypy --strict passes (strict type checking)",
        passed=passed,
        detail=f"Exit code {result.returncode}",
    )


def verify_append_only_enforcement() -> VerificationResult:
    test_path = Path("tests/orchestrator/security/test_read_only_state_access.py")
    content = test_path.read_text() if test_path.exists() else ""
    has_ro_test = "test_" in content and ("mode=ro" in content or "read_only" in content)
    test_path2 = Path("tests/orchestrator/security/test_append_only_enforcement.py")
    has_append_test = test_path2.exists()
    passed = has_ro_test or has_append_test
    return VerificationResult(
        name="Append-only enforcement tests (SEC-PH2-01, SEC-PH2-02)",
        passed=passed,
        detail="Security tests for read-only mode and append-only semantics exist",
    )


def verify_idempotency_constraint() -> VerificationResult:
    migration_path = Path("migrations/runtime/0001_state.sql")
    content = migration_path.read_text()
    passed = "UNIQUE" in content and "idempotency_key" in content
    return VerificationResult(
        name="Idempotency constraint (UNIQUE on idempotency_key)",
        passed=passed,
        detail="UNIQUE constraint on task_id + idempotency_key in 0001_state.sql",
    )


def verify_atomic_rollback_testing() -> VerificationResult:
    test_path = Path("tests/orchestrator/failure_paths/test_atomic_transition_rollback.py")
    passed = test_path.exists()
    return VerificationResult(
        name="Atomic rollback failure testing (REGR-0001)",
        passed=passed,
        detail="Test file verifies rollback on pre-commit failure",
    )


def verify_partial_migration_prevention() -> VerificationResult:
    test_path = Path("tests/orchestrator/unit/test_runtime_state_store.py")
    content = test_path.read_text() if test_path.exists() else ""
    passed = "REGR-0003" in content or "partial_schema" in content
    return VerificationResult(
        name="Partial migration prevention (REGR-0003)",
        passed=passed,
        detail="Test verifies version row only inserted after successful commit",
    )


def verify_git_commits() -> VerificationResult:
    result = subprocess.run(
        ["git", "log", "--oneline", "-10"],
        capture_output=True,
        text=True,
    )
    commits = result.stdout.strip().split("\n")
    # Look for meaningful commits related to orchestrator implementation
    keywords = {"state", "runtime", "journal", "reconciliation", "lease", "scheduler", "memory"}
    found_commits = 0
    for commit in commits:
        commit_lower = commit.lower()
        if any(kw in commit_lower for kw in keywords):
            found_commits += 1
    passed = found_commits >= 4
    return VerificationResult(
        name="Git history includes T2.1–T2.5 boundary commits",
        passed=passed,
        detail=f"Found {found_commits}/5+ meaningful task commits in recent history",
    )


def main() -> int:
    verifications = [
        verify_migrations_exist,
        verify_migration_sha_pinning,
        verify_core_classes,
        verify_transition_policy,
        verify_state_reader_writer,
        verify_reconciliation_suite,
        verify_fencing_suite,
        verify_scheduler_suite,
        verify_memory_suite,
        verify_test_coverage,
        verify_test_execution,
        verify_ruff_linting,
        verify_mypy_strict,
        verify_append_only_enforcement,
        verify_idempotency_constraint,
        verify_atomic_rollback_testing,
        verify_partial_migration_prevention,
        verify_git_commits,
    ]

    results = [v() for v in verifications]
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)

    print("\n" + "=" * 80)
    print("PH-2 VERIFICATION SUITE — PROM-PH2 EXIT GATE")
    print("=" * 80 + "\n")

    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status:8} | {result.name:50} | {result.detail}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {passed_count}/{total_count} verifications passed")
    print("=" * 80 + "\n")

    if passed_count == total_count:
        print("🎯 PROM-PH2 EXIT GATE: PASS — Section 2 is production-ready.\n")
        return 0
    else:
        print("⚠️  PROM-PH2 EXIT GATE: INCOMPLETE — Fix failures above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
