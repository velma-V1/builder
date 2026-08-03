#!/usr/bin/env python3
"""Verification suite for roadmap PH-3 Task RPH3-T3 (Approval Engine / CMP-APPROVAL).

Scoped gate for the approval domain only. It is NOT the PROM-RPH3 phase-exit gate — later RPH3 tasks
(permission, tools, watchdog) extend the phase suite. Builds on the accepted RPH3-T4 audit foundation.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _contains(path: str, *needles: str) -> tuple[bool, str]:
    p = Path(path)
    content = p.read_text() if p.exists() else ""
    missing = [n for n in needles if n not in content]
    return (not missing and bool(content)), f"missing={missing}" if missing else "ok"


def verify_migration_and_schema() -> VerificationResult:
    ok, detail = _contains(
        "migrations/security/0001_security_spine.sql",
        "CREATE TABLE approval_records",
        "CREATE TABLE approval_queue",
        "CREATE TABLE approval_intents",
        "commit_state",
        "prior_state",
        "requires_confirmation",
        "operation_class INTEGER NOT NULL CHECK (operation_class IN (1, 2, 3))",
    )
    return VerificationResult(
        "Approval migration: records + queue + intents (XSC §3.1 shape)", ok, detail
    )


def verify_migration_sha_pinning() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/approval/store.py", "0001_security_spine.sql", "_EXPECTED_MIGRATION_HASHES"
    )
    return VerificationResult("Security migration SHA-256 pinned in store.py", ok, detail)


def verify_models() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/approval/models.py",
        "class ApprovalState",
        "class CommitState",
        "class ApprovalCard",
        "def is_complete",
        "class ApprovalRecord",
        "class Denial",
        "def action_fingerprint",
    )
    return VerificationResult("Approval models (state, card, record, fingerprint)", ok, detail)


def verify_sole_writer_and_reader() -> VerificationResult:
    writer_ok, wdetail = _contains(
        "src/factory/approval/writer.py",
        "class _ApprovalWriter",
        "def stage_enqueue",
        "def stage_transition",
        "def commit_operation",
        "def rollback_operation",
    )
    reader_ok, rdetail = _contains(
        "src/factory/approval/store.py",
        "class SQLiteApprovalReader",
        "_approval_writer_authorizer",
        "mode=ro",
        "def audit_completion_seq",
    )
    init_ok, _ = _contains("src/factory/approval/__init__.py", "SQLiteApprovalReader")
    not_exported = "_ApprovalWriter" not in Path("src/factory/approval/__init__.py").read_text()
    ok = writer_ok and reader_ok and init_ok and not_exported
    return VerificationResult(
        "Private sole-writer + read-only reader (writer not exported)",
        ok,
        f"writer={wdetail}; reader={rdetail}; not_exported={not_exported}",
    )


def verify_engine() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/approval/engine.py",
        "class ApprovalEngine",
        "def enqueue",
        "def decide",
        "def consume",
        "def revoke",
        "def expire",
        "def is_valid",
        "def reconcile_startup",
        "APPROVAL_SECURITY_VIOLATION",
        "APPROVAL_AUDIT_CHAIN_INVALID",
    )
    return VerificationResult(
        "Engine: full lifecycle + Class-1 + reconcile + fail-closed", ok, detail
    )


def verify_tests_exist() -> VerificationResult:
    files = [
        "tests/approval/conftest.py",
        "tests/approval/unit/test_engine.py",
        "tests/approval/unit/test_engine_edges.py",
        "tests/approval/unit/test_store.py",
        "tests/approval/security/test_binding_and_reuse.py",
        "tests/approval/failure_paths/test_crash_reconciliation.py",
        "tests/approval/failure_paths/test_writer_faults.py",
        "tests/approval/integration/test_cross_store.py",
    ]
    present = [f for f in files if Path(f).exists()]
    return VerificationResult(
        "Approval test files (unit/store/security/failure-path/integration)",
        len(present) == len(files),
        f"{len(present)}/{len(files)} present",
    )


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/approval",
            "-q",
            "--cov=src/factory/approval",
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "Approval tests pass with >=95% branch coverage",
        result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/approval", "tests/approval"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "Ruff clean (approval src + tests)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/approval", "tests/approval", "--strict"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "mypy --strict clean (approval)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    verifications = [
        verify_migration_and_schema,
        verify_migration_sha_pinning,
        verify_models,
        verify_sole_writer_and_reader,
        verify_engine,
        verify_tests_exist,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("RPH3-T3 VERIFICATION SUITE — Approval Engine (CMP-APPROVAL)")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:58} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print(
            "RPH3-T3 gate: PASS (approval domain). NOT PROM-RPH3; NOT implementation of other tasks.\n"
        )
        return 0
    print("RPH3-T3 gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
