#!/usr/bin/env python3
"""Integrated verifier for the complete roadmap PH-3 security spine."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MIGRATION_SHA256 = {
    "migrations/audit/0001_audit_chain.sql": (
        "935e535a8db35693f94c6a30bcd9d312960eeeb24babea62e933ba7dfa06c433"
    ),
    "migrations/runtime/0001_state.sql": (
        "2fd4ecda34c05265be99de9c8aa36518cc9ac540c4038286c5da9cfb1fbd5f4c"
    ),
    "migrations/runtime/0002_leases.sql": (
        "a3a143e4b225655b68aadb5bc677acae7a99cf99b8c047e6c3113deb34b32ba6"
    ),
    "migrations/runtime/0003_memory.sql": (
        "65e0a4d16b84a49b205b1f2e48c91e11ae6dc48e9c179e318da3026283e10587"
    ),
    "migrations/runtime/0004_workstream_membership.sql": (
        "0274e9f2933b543277a4c50e556f8cc87762a69291e6b882d173c89811c4dc5f"
    ),
    "migrations/runtime/0005_task_requests.sql": (
        "a68ca07b5c48d494fc42e714828e6c54c3e13f9415b247db1965690b7aa65bc8"
    ),
    "migrations/runtime/0006_worker_runs.sql": (
        "38d36efe4cdbb2397da486271dce79d40fc88a737cca9fc6c8883f6134e0ba71"
    ),
    "migrations/runtime/0007_verification_promotion.sql": (
        "f0f8441120ae50e2732ccb7e3d74899a897b70db33ded820e36ed26697458556"
    ),
    "migrations/security/0001_security_spine.sql": (
        "099ae959d6f06c6b944925af151d8fa8dd2b65fdffd63660cf2a4355b7878a51"
    ),
    "migrations/security/0002_permission.sql": (
        "a65d227d9683eb060c834ae8b3cb65f33186ba37420b4065eec8623f8ded88cb"
    ),
    "migrations/security/0003_tools.sql": (
        "0050e74f80932fb58ea15d1f60f95661c7589d57dd623aad7691e26ea73a69b5"
    ),
    "migrations/security/0004_watchdog.sql": (
        "21ad8fa85055e1e55b703a55865a442b4e1af907c39baf668f7fcf34a4488b80"
    ),
}


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _contains(path: str, *needles: str) -> bool:
    file = Path(path)
    content = file.read_text(encoding="utf-8") if file.exists() else ""
    return bool(content) and all(needle in content for needle in needles)


def _inventory(paths: tuple[str, ...]) -> tuple[bool, str]:
    missing = [path for path in paths if not Path(path).exists()]
    return not missing, f"missing={missing}" if missing else f"{len(paths)}/{len(paths)} present"


def verify_complete_graph() -> VerificationResult:
    components = (
        "src/factory/watchdog",
        "src/factory/permission",
        "src/factory/approval",
        "src/factory/audit",
        "src/factory/tools",
        "src/factory/fileops",
        "src/factory/safemode",
    )
    missing = [component for component in components if not Path(component).is_dir()]
    bridge = _contains(
        "src/factory/watchdog/integration.py",
        "class RPH3CrossLaneBridge",
        "WatchdogInterventionReceiver",
        "PermissionDecision",
        "ApprovalRecord",
        "AuditValidator",
        "ToolResult",
        "FileOpError",
        "SafeMode",
    )
    return VerificationResult(
        "Complete Lane A/internal WIR/Lane B graph",
        not missing and bridge,
        f"missing={missing}; bridge={bridge}",
    )


def verify_ownership_and_no_bypass() -> VerificationResult:
    public_watchdog = Path("src/factory/watchdog/__init__.py").read_text(encoding="utf-8")
    bridge = Path("src/factory/watchdog/integration.py").read_text(encoding="utf-8")
    forbidden = (
        "ToolGateway(",
        "FileOpService(",
        "sqlite3.connect",
        "subprocess",
        "os.system",
        "Popen(",
    )
    found = [token for token in forbidden if token in bridge]
    private_writer = "_InterventionWriter" not in public_watchdog
    return VerificationResult(
        "Sole-writer/read-only boundaries and no cross-lane bypass",
        not found and private_writer,
        f"forbidden={found}; watchdog_writer_private={private_writer}",
    )


def verify_migration_manifest() -> VerificationResult:
    mismatches: list[str] = []
    for name, expected in MIGRATION_SHA256.items():
        path = Path(name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
        if actual != expected:
            mismatches.append(f"{name}:{actual}")
    sql_files = {
        path.as_posix()
        for root in ("migrations/audit", "migrations/runtime", "migrations/security")
        for path in Path(root).glob("*.sql")
    }
    undeclared = sorted(sql_files - set(MIGRATION_SHA256))
    return VerificationResult(
        "Exact ordered migration manifest and SHA-256 values",
        not mismatches and not undeclared,
        f"hashes={len(MIGRATION_SHA256)}; mismatches={mismatches}; undeclared={undeclared}",
    )


def verify_database_lifecycle_inventory() -> VerificationResult:
    ok, detail = _inventory(
        (
            "tests/orchestrator/unit/test_runtime_state_store.py",
            "tests/approval/unit/test_store.py",
            "tests/permission/unit/test_permission_store.py",
            "tests/tools/unit/test_tool_store.py",
            "tests/audit/unit/test_audit_writer.py",
            "tests/watchdog/test_watchdog_store.py",
            "tests/contracts/security/test_migration_checkout_portability.py",
        )
    )
    return VerificationResult(
        "Fresh/existing/idempotent/tamper/rollback migration lifecycle inventory",
        ok,
        detail,
    )


def verify_security_abuse_inventory() -> VerificationResult:
    ok, detail = _inventory(
        (
            "tests/permission/security/test_least_privilege_and_paths.py",
            "tests/approval/security/test_binding_and_reuse.py",
            "tests/audit/security/test_audit_append_only_and_cardinality.py",
            "tests/tools/security/test_tool_security.py",
            "tests/fileops/test_fileops_edges.py",
            "tests/watchdog/test_interventions_security.py",
            "tests/rph3_integration/test_cross_lane_security.py",
        )
    )
    return VerificationResult(
        "Permission/approval/gateway/path/audit/watchdog abuse inventory",
        ok,
        detail,
    )


def verify_crash_recovery_inventory() -> VerificationResult:
    ok, detail = _inventory(
        (
            "tests/watchdog/test_interventions_failure_path.py",
            "tests/approval/failure_paths/test_crash_reconciliation.py",
            "tests/permission/failure_paths/test_permission_crash_reconciliation.py",
            "tests/audit/failure_paths/test_partial_write_and_corruption.py",
            "tests/tools/failure_paths/test_tool_faults.py",
            "tests/rph3_integration/test_cross_lane_failure_paths.py",
        )
    )
    return VerificationResult(
        "Crash windows, stale/conflicting state, store failure, reconciliation inventory",
        ok,
        detail,
    )


def verify_end_to_end_inventory() -> VerificationResult:
    ok, detail = _inventory(
        (
            "tests/rph3_integration/test_full_cross_lane_flow.py",
            "tests/rph3_integration/test_cross_lane_unit.py",
            "tests/rph3_integration/test_cross_lane_approval.py",
            "tests/rph3_integration/test_cross_lane_tools_fileops.py",
        )
    )
    return VerificationResult(
        "Healthy/denied/intervened/Safe Mode/restart/concurrent end-to-end inventory",
        ok,
        detail,
    )


def verify_focused_integration() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/watchdog",
            "tests/permission",
            "tests/approval",
            "tests/audit",
            "tests/tools",
            "tests/fileops",
            "tests/safemode",
            "tests/rph3_integration",
            "-q",
            "-W",
            "error::ResourceWarning",
            "-W",
            "error::pytest.PytestUnraisableExceptionWarning",
        ],
        capture_output=True,
        text=True,
    )
    summary = (result.stdout.strip().splitlines() or ["?"])[-1]
    return VerificationResult(
        "All RPH3 component/cross-lane tests + SQLite warning regression",
        result.returncode == 0,
        f"exit={result.returncode}; {summary}",
    )


def verify_evidence_inventory() -> VerificationResult:
    ok, detail = _inventory(
        (
            "docs/verification/roadmap-ph3-evidence-report.md",
            "docs/verification/roadmap-ph3-requirement-to-test-matrix.md",
            "docs/verification/roadmap-ph3-failure-path-matrix.md",
            "docs/verification/roadmap-ph3-migration-manifest.md",
            "docs/verification/roadmap-ph3-windows-matrix.md",
            "docs/verification/roadmap-ph3-warning-skip-register.md",
            "docs/verification/roadmap-ph3-risk-register.md",
            "docs/verification/roadmap-ph3-promotion-readiness.md",
        )
    )
    return VerificationResult("Final RPH3 evidence package inventory", ok, detail)


def verify_static() -> VerificationResult:
    ruff = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "scripts/verify_roadmap_ph3.py",
            "tests/approval/failure_paths/test_writer_faults.py",
        ],
        capture_output=True,
        text=True,
    )
    mypy = subprocess.run(
        [sys.executable, "-m", "mypy", "scripts/verify_roadmap_ph3.py", "--strict"],
        capture_output=True,
        text=True,
    )
    return VerificationResult(
        "Integrated verifier Ruff + mypy --strict",
        ruff.returncode == 0 and mypy.returncode == 0,
        f"ruff={ruff.returncode}; mypy={mypy.returncode}",
    )


def main() -> int:
    checks = (
        verify_complete_graph,
        verify_ownership_and_no_bypass,
        verify_migration_manifest,
        verify_database_lifecycle_inventory,
        verify_security_abuse_inventory,
        verify_crash_recovery_inventory,
        verify_end_to_end_inventory,
        verify_focused_integration,
        verify_evidence_inventory,
        verify_static,
    )
    results = [check() for check in checks]
    print("\n" + "=" * 80)
    print("RPH3 INTEGRATED SECURITY-SPINE VERIFICATION SUITE")
    print("=" * 80 + "\n")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:5} | {result.name:66} | {result.detail}")
    passed = sum(result.passed for result in results)
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{len(results)} checks passed")
    print("=" * 80 + "\n")
    if passed == len(results):
        print("RPH3 integrated gate: PASS. Operator promotion review remains required.\n")
        return 0
    print("RPH3 integrated gate: INCOMPLETE - fix failures above.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
