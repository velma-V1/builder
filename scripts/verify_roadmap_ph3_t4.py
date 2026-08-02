#!/usr/bin/env python3
"""Verification suite for roadmap PH-3 Task RPH3-T4 (audit writer + chain validator).

Scoped gate for the audit foundation only (CMP-AUDITW / CMP-AUDITV). It is NOT the PROM-RPH3
phase-exit gate — later RPH3 tasks (approval, permission, tools, watchdog) extend the phase suite.
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
        "migrations/audit/0001_audit_chain.sql",
        "CREATE TABLE audit_records",
        "record_kind IN ('INTENT', 'COMPLETION')",
        "UNIQUE (op_key, record_kind)",
        "audit_records_no_update",
        "audit_records_no_delete",
    )
    return VerificationResult(
        "Audit migration: append-only + UNIQUE(op_key, record_kind)", ok, detail
    )


def verify_migration_sha_pinning() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/audit/writer.py", "0001_audit_chain.sql", "_EXPECTED_MIGRATION_HASHES"
    )
    return VerificationResult("Audit migration SHA-256 pinned in writer.py", ok, detail)


def verify_models() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/audit/models.py",
        "class RecordKind",
        "INTENT",
        "COMPLETION",
        "class AuditRecord",
        "class AuditEvent",
        "class BreakClass",
        "def compute_hash",
    )
    return VerificationResult(
        "Audit models (RecordKind, AuditRecord, AuditEvent, BreakClass)", ok, detail
    )


def verify_writer() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/audit/writer.py",
        "class AuditWriter",
        "def append",
        "AUDIT_DUPLICATE",
        "AUDIT_COMPLETION_BEFORE_INTENT",
        "AUDIT_INTENT_ONLY_CLASS3",
    )
    return VerificationResult("Audit writer: append + cardinality + Class-3 ordering", ok, detail)


def verify_validator() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/audit/validator.py",
        "class AuditValidator",
        "def verify_chain",
        "def classify_break",
        "DELETION",
        "TRUNCATION",
        "REORDER",
        "REWRITE",
        "BAD_ANCHOR",
    )
    return VerificationResult("Audit validator: verify_chain + break classification", ok, detail)


def verify_tests_exist() -> VerificationResult:
    files = [
        "tests/audit/conftest.py",
        "tests/audit/unit/test_audit_writer.py",
        "tests/audit/unit/test_audit_validator.py",
        "tests/audit/security/test_audit_append_only_and_cardinality.py",
        "tests/audit/failure_paths/test_partial_write_and_corruption.py",
        "tests/audit/failure_paths/test_writer_injection.py",
    ]
    present = [f for f in files if Path(f).exists()]
    return VerificationResult(
        "Audit test files (unit/security/failure-path)",
        len(present) == len(files),
        f"{len(present)}/{len(files)} present",
    )


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/audit",
            "-q",
            "--cov=src/factory/audit",
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "Audit tests pass with >=95% branch coverage",
        result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/audit", "tests/audit"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "Ruff clean (audit src + tests)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/audit", "tests/audit", "--strict"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "mypy --strict clean (audit)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    verifications = [
        verify_migration_and_schema,
        verify_migration_sha_pinning,
        verify_models,
        verify_writer,
        verify_validator,
        verify_tests_exist,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("RPH3-T4 VERIFICATION SUITE — audit writer + chain validator")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:56} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print(
            "RPH3-T4 gate: PASS (audit foundation). NOT PROM-RPH3; NOT implementation of other tasks.\n"
        )
        return 0
    print("RPH3-T4 gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
