#!/usr/bin/env python3
"""Verification suite for roadmap PH-3 Task RPH3-T2 (Permission Enforcement / CMP-PERM).

Scoped gate for the permission domain only. It is NOT the PROM-RPH3 phase-exit gate. Builds on the
accepted RPH3-T4 audit foundation and the RPH3-T3 approval domain (shared security-spine store).
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
        "migrations/security/0002_permission.sql",
        "CREATE TABLE permission_grants",
        "CREATE TABLE permission_intents",
        "commit_state",
        "prior_state",
        "grant_fingerprint",
        "CREATE TABLE IF NOT EXISTS schema_migrations",
    )
    return VerificationResult(
        "Permission migration: grants + intents (ordered per-domain 0002)", ok, detail
    )


def verify_migration_sha_pinning() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/permission/store.py", "0002_permission.sql", "_EXPECTED_MIGRATION_HASHES"
    )
    return VerificationResult("Permission migration SHA-256 pinned in store.py", ok, detail)


def verify_models_and_autonomy() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/permission/models.py",
        "class PermissionState",
        "class DecisionKind",
        "class PermissionClass",
        "class PermissionGrant",
        "def grant_fingerprint",
        "class TaskAuthority",
    )
    ok2, d2 = _contains(
        "src/factory/permission/autonomy.py",
        "class AutonomyEnvelope",
        "def classify",
        "REQUIRES_CARD",
    )
    return VerificationResult(
        "Permission models + autonomy envelope (Decision A)", ok and ok2, f"{detail}; autonomy={d2}"
    )


def verify_sole_writer_and_reader() -> VerificationResult:
    writer_ok, wdetail = _contains(
        "src/factory/permission/writer.py",
        "class _PermissionWriter",
        "def stage_issue",
        "def stage_transition",
        "def commit_operation",
        "def rollback_operation",
    )
    reader_ok, rdetail = _contains(
        "src/factory/permission/store.py",
        "class SQLitePermissionReader",
        "_permission_writer_authorizer",
        "mode=ro",
        "def audit_completion_seq",
    )
    not_exported = "_PermissionWriter" not in Path("src/factory/permission/__init__.py").read_text()
    ok = writer_ok and reader_ok and not_exported
    return VerificationResult(
        "Private sole-writer + read-only reader (writer not exported)",
        ok,
        f"writer={wdetail}; reader={rdetail}; not_exported={not_exported}",
    )


def verify_engine() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/permission/engine.py",
        "class PermissionEngine",
        "def decide",
        "def issue_grant",
        "def revalidate",
        "def revoke",
        "def expire",
        "def canonicalize",
        "def reconcile_startup",
        "APPROVAL_REQUIRED_CLASSES",
        "PERMISSION_AUDIT_CHAIN_INVALID",
    )
    return VerificationResult(
        "Engine: least-privilege decide + grant + TOCTOU + Class-1 + reconcile", ok, detail
    )


def verify_path_authority_reuse() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/permission/engine.py",
        "from factory.contracts.validation.paths import PathAuthority",
    )
    return VerificationResult(
        "Path authority reuses the tested PathAuthority (escape-blocking)", ok, detail
    )


def verify_tests_exist() -> VerificationResult:
    files = [
        "tests/permission/conftest.py",
        "tests/permission/unit/test_permission_engine.py",
        "tests/permission/unit/test_permission_engine_edges.py",
        "tests/permission/unit/test_autonomy.py",
        "tests/permission/unit/test_permission_store.py",
        "tests/permission/security/test_least_privilege_and_paths.py",
        "tests/permission/failure_paths/test_permission_crash_reconciliation.py",
        "tests/permission/failure_paths/test_permission_writer_faults.py",
        "tests/permission/integration/test_permission_cross_store.py",
    ]
    present = [f for f in files if Path(f).exists()]
    return VerificationResult(
        "Permission test files (unit/store/autonomy/security/failure-path/integration)",
        len(present) == len(files),
        f"{len(present)}/{len(files)} present",
    )


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/permission",
            "-q",
            "--cov=src/factory/permission",
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "Permission tests pass with >=95% branch coverage",
        result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/permission", "tests/permission"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "Ruff clean (permission src + tests)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/permission", "tests/permission", "--strict"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "mypy --strict clean (permission)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    verifications = [
        verify_migration_and_schema,
        verify_migration_sha_pinning,
        verify_models_and_autonomy,
        verify_sole_writer_and_reader,
        verify_engine,
        verify_path_authority_reuse,
        verify_tests_exist,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("RPH3-T2 VERIFICATION SUITE — Permission Enforcement (CMP-PERM)")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:60} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print(
            "RPH3-T2 gate: PASS (permission domain). NOT PROM-RPH3; NOT implementation of other tasks.\n"
        )
        return 0
    print("RPH3-T2 gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
