#!/usr/bin/env python3
"""Dedicated verifier for repository-defined RPH3 Lane A / Lane B wiring."""

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
    file = Path(path)
    content = file.read_text(encoding="utf-8") if file.exists() else ""
    missing = [needle for needle in needles if needle not in content]
    return not missing and bool(content), f"missing={missing}" if missing else "ok"


def verify_bridge() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/watchdog/integration.py",
        "class RPH3CrossLaneBridge",
        "class LaneBSignal",
        "class CrossLaneResult",
        "def from_permission",
        "def from_approval",
        "def from_tool_gateway",
        "def from_fileop",
        "def audit_health",
        "def dependency_failure",
        "def request_safe_mode",
    )
    return VerificationResult("Typed cross-lane adapter inside CMP-WATCH", ok, detail)


def verify_real_interfaces() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/watchdog/integration.py",
        "from factory.approval import ApprovalRecord",
        "from factory.audit import AuditValidator",
        "from factory.fileops import FileOpError",
        "PermissionDecision",
        "from factory.safemode import SafeMode",
        "from factory.tools import ToolResult",
        "WatchdogInterventionReceiver",
    )
    return VerificationResult("Consumes accepted Lane B public result interfaces", ok, detail)


def verify_fail_closed() -> VerificationResult:
    ok, detail = _contains(
        "src/factory/watchdog/integration.py",
        "conflicting cross-lane message",
        "invalid or unbounded cross-lane message",
        "WIR delivery failed closed",
        "InterventionCommand.PAUSE_TASK",
        "InterventionCommand.CONTAIN_TASK",
        "CrossLaneOutcome.DENIED",
        "safe_mode.enter",
    )
    return VerificationResult(
        "Deterministic denial/intervention/Safe Mode failure propagation", ok, detail
    )


def verify_no_bypass() -> VerificationResult:
    source = Path("src/factory/watchdog/integration.py").read_text(encoding="utf-8")
    forbidden = (
        "ToolGateway(",
        "FileOpService(",
        "sqlite3.connect",
        "subprocess",
        "os.system",
        "open(",
    )
    found = [token for token in forbidden if token in source]
    return VerificationResult(
        "No tool/file/store/host bypass path",
        not found,
        f"forbidden_found={found}",
    )


def verify_test_inventory() -> VerificationResult:
    expected = {
        "test_cross_lane_unit.py",
        "test_cross_lane_approval.py",
        "test_cross_lane_tools_fileops.py",
        "test_cross_lane_failure_paths.py",
        "test_cross_lane_security.py",
        "test_full_cross_lane_flow.py",
    }
    present = {path.name for path in Path("tests/rph3_integration").glob("test_*.py")}
    missing = sorted(expected - present)
    return VerificationResult(
        "Cross-lane unit/security/failure/concurrency/end-to-end tests",
        not missing,
        f"missing={missing}" if missing else f"{len(present)}/{len(expected)} present",
    )


def verify_tests() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/rph3_integration",
            "-q",
            "--cov=factory.watchdog.integration",
            "--cov-branch",
            "--cov-fail-under=95",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().splitlines() or ["?"])[-1]
    return VerificationResult(
        "Cross-lane tests pass with >=95% branch coverage",
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
            "src/factory/watchdog/integration.py",
            "tests/rph3_integration",
            "scripts/verify_roadmap_ph3_cross_lane.py",
        ],
        capture_output=True,
        text=True,
    )
    mypy = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "src/factory/watchdog/integration.py",
            "tests/rph3_integration",
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
        verify_bridge,
        verify_real_interfaces,
        verify_fail_closed,
        verify_no_bypass,
        verify_test_inventory,
        verify_tests,
        verify_static,
    )
    results = [check() for check in checks]
    print("\n" + "=" * 80)
    print("RPH3 CROSS-LANE VERIFICATION SUITE - Lane A CMP-WATCH + accepted Lane B")
    print("=" * 80 + "\n")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:5} | {result.name:58} | {result.detail}")
    passed = sum(result.passed for result in results)
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{len(results)} checks passed")
    print("=" * 80 + "\n")
    if passed == len(results):
        print("RPH3 cross-lane gate: PASS. NOT PROM-RPH3; integrated verification remains.\n")
        return 0
    print("RPH3 cross-lane gate: INCOMPLETE - fix failures above.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
