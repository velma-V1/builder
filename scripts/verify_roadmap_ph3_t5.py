#!/usr/bin/env python3
"""Verification suite for roadmap PH-3 Task RPH3-T5 (Tools enforcement gate).

Scoped gate for CMP-TOOLREG + CMP-TOOLGW + CMP-FILEOP + CMP-DIAG (Safe Mode). NOT the PROM-RPH3
phase-exit gate. Builds on the accepted RPH3-T4 audit foundation and the RPH3-T3/T2 domains (shared
security-spine store). RPH3 performs no direct host execution — actual OS enforcement is PH-5.
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


def verify_migration() -> VerificationResult:
    ok, detail = _contains(
        "migrations/security/0003_tools.sql",
        "CREATE TABLE tool_registry",
        "CREATE TABLE tool_declarations",
        "CREATE TABLE tool_quarantine",
        "CREATE TABLE tool_registry_intents",
        "CREATE TABLE IF NOT EXISTS schema_migrations",
    )
    ok2, _ = _contains("src/factory/tools/store.py", "0003_tools.sql", "_EXPECTED_MIGRATION_HASHES")
    return VerificationResult("Tool migration (0003) + SHA pin", ok and ok2, detail)


def verify_registry() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/tools/registry.py",
        "class ToolRegistry",
        "def register",
        "def lookup",
        "def quarantine",
        "def release",
        "def record_failure",
        "def reconcile_startup",
        "default-DENY",
        "QUARANTINE_FAILURE_THRESHOLD",
    )
    return VerificationResult(
        "Registry: default-deny + declaration/provenance + quarantine", ok, detail
    )


def verify_gateway() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/tools/gateway.py",
        "class ToolGateway",
        "def invoke",
        "def validate_output",
        "def enforce_limits",
        "def terminate_tree",
        "NO_SANDBOX_EXECUTOR",
        "LIMIT_INCREASE_REQUIRES_APPROVAL",
        "no direct host execution",
    )
    return VerificationResult(
        "Gateway: no-bypass + TOCTOU + limits + output validation", ok, detail
    )


def verify_fileop() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/fileops/service.py",
        "class FileOpService",
        "def canonicalize",
        "def write_atomic",
        "def delete",
        "def extract_archive",
        "FILEOP_DELETE_REQUIRES_APPROVAL",
        "operation_class=3",
        "from factory.contracts.validation.paths import PathAuthority",
    )
    return VerificationResult(
        "FileOp: path safety + Decision-B delete (Class-3) + archive caps", ok, detail
    )


def verify_safemode() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/safemode/__init__.py",
        "class SafeMode",
        "def enter",
        "def inspect",
        "def export_evidence",
        "def approved_repair",
        "SAFEMODE_UNAPPROVED",
        "SAFEMODE_OUT_OF_SCOPE",
        "no autonomous-write",
    )
    return VerificationResult(
        "Safe Mode: no autonomous write, approval+perm-gated repair", ok, detail
    )


def verify_isolation() -> VerificationResult:
    not_exported = "_ToolWriter" not in Path("src/factory/tools/__init__.py").read_text()
    ok, detail = _contains("src/factory/tools/store.py", "_tool_writer_authorizer", "mode=ro")
    return VerificationResult(
        "Sole-writer partition + read-only reader (writer not exported)",
        ok and not_exported,
        f"{detail}; not_exported={not_exported}",
    )


def _pytest(path: str, cov: str) -> tuple[bool, str]:
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            path,
            "-q",
            f"--cov={cov}",
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return result.returncode == 0, f"exit {result.returncode}; {summary}"


def verify_tools_tests() -> VerificationResult:
    ok, detail = _pytest("tests/tools", "src/factory/tools")
    return VerificationResult("Tool tests pass with >=95% coverage", ok, detail)


def verify_fileop_tests() -> VerificationResult:
    ok, detail = _pytest("tests/fileops", "src/factory/fileops")
    return VerificationResult("FileOp tests pass with >=95% coverage", ok, detail)


def verify_safemode_tests() -> VerificationResult:
    ok, detail = _pytest("tests/safemode", "src/factory/safemode")
    return VerificationResult("Safe Mode tests pass with >=95% coverage", ok, detail)


def verify_static() -> VerificationResult:
    ruff = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src/factory/tools",
            "src/factory/fileops",
            "src/factory/safemode",
            "tests/tools",
            "tests/fileops",
            "tests/safemode",
        ],
        capture_output=True,
        text=True,
    )
    mypy_ok = True
    for pkg in ("tools", "fileops", "safemode"):
        r = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "mypy", f"src/factory/{pkg}", f"tests/{pkg}", "--strict"],
            capture_output=True,
            text=True,
        )
        mypy_ok = mypy_ok and r.returncode == 0
    ok = ruff.returncode == 0 and mypy_ok
    return VerificationResult(
        "Ruff + mypy --strict clean (per package)", ok, f"ruff={ruff.returncode}; mypy_ok={mypy_ok}"
    )


def main() -> int:
    verifications = [
        verify_migration,
        verify_registry,
        verify_gateway,
        verify_fileop,
        verify_safemode,
        verify_isolation,
        verify_tools_tests,
        verify_fileop_tests,
        verify_safemode_tests,
        verify_static,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("RPH3-T5 VERIFICATION SUITE — Tools enforcement (TOOLREG/TOOLGW/FILEOP/DIAG)")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:58} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print("RPH3-T5 gate: PASS (tools enforcement). NOT PROM-RPH3; Lane A / Watchdog paused.\n")
        return 0
    print("RPH3-T5 gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
