#!/usr/bin/env python3
"""Verification suite for Stage-3 live-gate PREPARATION (deterministic; no live probes).

Confirms the preparation artifacts are present, typed, tested, and internally consistent, and that
the safety posture holds: the SQLite gate fails closed below the floor, the durable schema is
SHA-pinned, the Compose templates satisfy the hardened topology, and the acceptance matrices are
well-formed. It runs NO host probe and installs/starts NOTHING. It is NOT a phase-promotion gate:
SQLITE_REMEDIATION := PREPARED_NOT_EXECUTED and PH-4/5/6 remain LIVE_*_PENDING / NOT_AUTHORIZED.

Run under the project environment, e.g. ``.venv/bin/python scripts/verify_stage3_livegate_prep.py``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _exists(*rel: str) -> tuple[bool, str]:
    missing = [p for p in rel if not (ROOT / p).exists()]
    return (not missing), ("ok" if not missing else f"missing={missing}")


def verify_owned_path_layout() -> VerificationResult:
    ok, detail = _exists(
        "src/factory/livegate/__init__.py",
        "src/factory/livegate/models.py",
        "src/factory/livegate/redaction.py",
        "src/factory/livegate/sqlite_compliance.py",
        "src/factory/livegate/compose_topology.py",
        "src/factory/livegate/version_probe.py",
        "src/factory/livegate/adapter_contracts.py",
        "src/factory/livegate/durable_schema.py",
        "src/factory/livegate/acceptance.py",
        "scripts/live_gate/run_readiness.py",
    )
    return VerificationResult("livegate modules present at owner paths", ok, detail)


def verify_sqlite_gate_fails_closed() -> VerificationResult:
    from factory.livegate.models import CheckStatus
    from factory.livegate.sqlite_compliance import (
        durable_activation_fails_closed_below_floor,
        evaluate_sqlite_compliance,
    )

    below = evaluate_sqlite_compliance(version=(3, 50, 4))
    at_floor = evaluate_sqlite_compliance(version=(3, 51, 3))
    fails_closed = durable_activation_fails_closed_below_floor()
    ok = (
        below.status is CheckStatus.FAIL
        and below.mandatory
        and at_floor.status is CheckStatus.PASS
        and fails_closed
    )
    detail = (
        f"below_floor={below.status.value}; at_floor={at_floor.status.value}; "
        f"fail_closed={fails_closed}"
    )
    return VerificationResult("SQLite gate fails closed below floor (first gate)", ok, detail)


def verify_compose_topology() -> VerificationResult:
    import yaml

    from factory.livegate.compose_topology import validate_compose

    compose_dir = ROOT / "deploy" / "compose"
    workers = yaml.safe_load((compose_dir / "factory-workers.compose.yaml").read_text("utf-8"))
    broker = yaml.safe_load((compose_dir / "factory-broker.compose.yaml").read_text("utf-8"))
    worker_v = validate_compose(workers)
    broker_v = validate_compose(broker, broker_services=frozenset({"broker"}))
    ok = worker_v == () and broker_v == ()
    detail = f"worker_violations={len(worker_v)}; broker_violations={len(broker_v)}"
    return VerificationResult("Unapplied Compose templates satisfy hardened topology", ok, detail)


def verify_durable_schema_pinned() -> VerificationResult:
    from factory.livegate.durable_schema import validate_manifest

    problems = validate_manifest(ROOT)
    return VerificationResult(
        "Durable schema is SHA-256 pinned + unapplied", not problems,
        "ok" if not problems else f"problems={list(problems)}",
    )


def verify_acceptance_matrices() -> VerificationResult:
    from factory.livegate.acceptance import all_criteria

    criteria = all_criteria()
    ids = [c.criterion_id for c in criteria]
    ok = (
        len(criteria) == 18
        and len(ids) == len(set(ids))
        and all(c.mandatory and c.fake_parity for c in criteria)
    )
    return VerificationResult(
        "PH-4/5/6 acceptance matrices well-formed (18 criteria)", ok, f"count={len(criteria)}"
    )


def verify_adapter_contract_parity() -> VerificationResult:
    from factory.livegate.adapter_contracts import structural_parity_violations
    from factory.models.ollama_adapter.fake_ollama import FakeOllamaAdapter
    from factory.workers.aider_adapter.fake_aider import FakeAiderWorker

    ollama_v = structural_parity_violations(FakeOllamaAdapter())
    aider_v = structural_parity_violations(FakeAiderWorker())
    non_adapter = structural_parity_violations(object())
    ok = ollama_v == () and aider_v == () and bool(non_adapter)
    return VerificationResult(
        "Fakes are structural drop-ins for the live adapter contract", ok,
        f"ollama={len(ollama_v)}; aider={len(aider_v)}; rejects_non_adapter={bool(non_adapter)}",
    )


def verify_discovery_output_ignored() -> VerificationResult:
    git = shutil.which("git")
    if git is None:  # pragma: no cover - git is a dev dependency
        return VerificationResult("Discovery output path is git-ignored", False, "git not found")
    result = subprocess.run(  # noqa: S603 - fixed args, resolved absolute git
        [git, "check-ignore", ".livegate-out/readiness.json"],
        capture_output=True, text=True, cwd=ROOT,
    )
    ok = result.returncode == 0 and ".livegate-out" in result.stdout
    return VerificationResult("Discovery output path is git-ignored", ok, f"exit {result.returncode}")


def verify_tests_pass() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/livegate", "-q"],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("livegate tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "src/factory/livegate", "tests/livegate", "scripts/live_gate",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("Ruff clean (livegate)", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy",
            "src/factory/livegate", "tests/livegate", "scripts/live_gate", "--strict",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("mypy --strict clean (livegate)", result.returncode == 0, f"exit {result.returncode}")


def verify_evidence_present() -> VerificationResult:
    ok, detail = _exists(
        "docs/live-gate/00-OVERVIEW.md",
        "docs/live-gate/01-host-environment-inventory.md",
        "docs/live-gate/02-wsl2-docker-readiness.md",
        "docs/live-gate/03-nvidia-cuda-compatibility.md",
        "docs/live-gate/04-ollama-model-availability.md",
        "docs/live-gate/05-sqlite-compliance-and-remediation.md",
        "docs/live-gate/06-live-gate-acceptance-criteria.md",
        "docs/live-gate/07-rollback-and-cleanup.md",
        "docs/live-gate/08-OPERATOR-ACTIONS-REQUIRED.md",
        "docs/live-gate/09-evidence-record-templates.md",
        "deploy/compose/README.md",
    )
    return VerificationResult("Stage-3 evidence package present", ok, detail)


def main() -> int:
    verifications = [
        verify_owned_path_layout,
        verify_sqlite_gate_fails_closed,
        verify_compose_topology,
        verify_durable_schema_pinned,
        verify_acceptance_matrices,
        verify_adapter_contract_parity,
        verify_discovery_output_ignored,
        verify_tests_pass,
        verify_ruff,
        verify_mypy,
        verify_evidence_present,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("STAGE-3 LIVE-GATE PREPARATION VERIFICATION SUITE (deterministic; no live probes)")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:60} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print(
            "Stage-3 preparation gate: PASS. SQLITE_REMEDIATION=PREPARED_NOT_EXECUTED; "
            "PH-4/5/6 LIVE_*_PENDING; PROM NOT_AUTHORIZED; not a phase promotion.\n"
        )
        return 0
    print("Stage-3 preparation gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
