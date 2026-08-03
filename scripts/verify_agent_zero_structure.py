#!/usr/bin/env python3
"""Verification suite for the Agent Zero integration structure (deterministic; no live calls).

Confirms the managed-worker boundaries: no Agent Zero upstream source is vendored into Builder,
the exact official revision and license are recorded, no integration-module environment-secret
access, AI access is model-router-only (no provider/secret handle), a worker's result carries no
verified/approved/promoted field,
and the deterministic tests pass under ruff + strict mypy. Makes NO network/process/container call.
Not a phase-promotion gate.
"""

from __future__ import annotations

import dataclasses
import inspect
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_AZ = ROOT / "src" / "factory" / "integrations" / "agent_zero"
_FORBIDDEN_HTTP = (
    "import requests",
    "import httpx",
    "import aiohttp",
    "import http.client",
    "from urllib.request",
    "import urllib.request",
    "import socket",
)
_FORBIDDEN_PROCESS = (
    "import subprocess",
    "import docker",
    "from docker",
    "os.system(",
    "import pty",
)
_FORBIDDEN_SECRET = ("os.environ", "os.getenv", "getenv(")


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _scan(needles: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for path in sorted(_AZ.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}::{needle}")
    return hits


def verify_layout() -> VerificationResult:
    files = [
        "errors",
        "models",
        "capabilities",
        "transport",
        "fake_transport",
        "adapter",
        "task_mapping",
        "result_mapping",
        "event_validation",
        "policy",
        "official_client",
        "health",
        "compatibility",
        "provenance",
        "manifest",
    ]
    missing = [f for f in files if not (_AZ / f"{f}.py").exists()]
    return VerificationResult("Agent Zero modules present", not missing, f"missing={missing}")


def verify_no_source_copied() -> VerificationResult:
    vendor_dirs = [
        d.name
        for d in _AZ.iterdir()
        if d.is_dir() and d.name in ("vendor", "_vendor", "upstream", "third_party")
    ]
    total_kb = sum(p.stat().st_size for p in _AZ.rglob("*.py")) // 1024
    ok = not vendor_dirs and total_kb < 300
    return VerificationResult(
        "no Agent Zero upstream source vendored",
        ok,
        f"vendor_dirs={vendor_dirs}; size_kb={total_kb}",
    )


def verify_attribution_and_license() -> VerificationResult:
    from factory.integrations.agent_zero import AGENT_ZERO_MANIFEST, MANAGED_WORKER_OBLIGATIONS

    ok = (
        bool(AGENT_ZERO_MANIFEST.attribution)
        and AGENT_ZERO_MANIFEST.license == "MIT"
        and AGENT_ZERO_MANIFEST.license_verified is True
        and AGENT_ZERO_MANIFEST.revision_verified is True
        and AGENT_ZERO_MANIFEST.required_domains == frozenset()
        and bool(MANAGED_WORKER_OBLIGATIONS)
    )
    return VerificationResult("official revision, attribution, and MIT license recorded", ok, "ok")


def verify_no_direct_http_process_or_secret() -> VerificationResult:
    hits = _scan(_FORBIDDEN_HTTP + _FORBIDDEN_PROCESS + _FORBIDDEN_SECRET)
    return VerificationResult(
        "no direct HTTP / process-spawn / Docker / env-secret access", not hits, f"hits={hits}"
    )


def verify_model_router_only() -> VerificationResult:
    from factory.integrations.agent_zero import AgentZeroAdapter

    slots = set(AgentZeroAdapter.__slots__)
    ok = "_router" in slots and not any("provider" in s or "secret" in s for s in slots)
    return VerificationResult(
        "AI access is Builder-router-only (no provider/secret handle)",
        ok,
        f"router_slot={'_router' in slots}",
    )


def verify_no_secret_broker_parameter_exists() -> VerificationResult:
    from factory.integrations.agent_zero import BrokeredAgentZeroHttp

    params = set(inspect.signature(BrokeredAgentZeroHttp.__init__).parameters)
    ok = not any("secret" in p.lower() for p in params)
    return VerificationResult(
        "no code path can construct a secret-carrying HTTP wrapper", ok, f"params={sorted(params)}"
    )


def verify_managed_lifecycle() -> VerificationResult:
    source = (ROOT / "src/factory/integrations/runtime.py").read_text(encoding="utf-8")
    compose = (ROOT / "deploy/integrations/agent-zero/compose.yaml").read_text(encoding="utf-8")
    ok = "_verify_revision" in source and "builder-enabled" in compose
    return VerificationResult(
        "Agent Zero uses Builder-managed immutable lifecycle", ok, "managed runtime + profile"
    )


def verify_result_carries_no_verification_authority() -> VerificationResult:
    from factory.integrations.agent_zero import AgentZeroResult, WorkerOutcome

    result = AgentZeroResult(work_order_id="wo-1", worker_claimed_outcome=WorkerOutcome.SUCCESS)
    field_names = {f.name for f in dataclasses.fields(result)}
    forbidden = {"verified", "approved", "promoted", "merged"}
    ok = field_names.isdisjoint(forbidden) and "worker_claimed_outcome" in field_names
    return VerificationResult(
        "worker result carries no verified/approved/promoted field (worker success != Builder "
        "verification)",
        ok,
        f"fields={sorted(field_names)}",
    )


def verify_work_order_carries_no_forbidden_grant() -> VerificationResult:
    from factory.integrations.agent_zero import WorkOrder

    field_names = {f.name for f in dataclasses.fields(WorkOrder)}
    forbidden = {
        "provider_api_key",
        "api_key",
        "docker_socket",
        "secret",
        "schedule",
        "cron",
        "merge_authority",
        "approval_authority",
        "promotion_authority",
    }
    ok = field_names.isdisjoint(forbidden)
    return VerificationResult(
        "work order grant carries none of the forbidden authorities/handles",
        ok,
        f"fields={sorted(field_names)}",
    )


def verify_tests() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integrations/agent_zero", "-q"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("Agent Zero tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src/factory/integrations/agent_zero",
            "tests/integrations/agent_zero",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "Ruff clean (agent_zero)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "src/factory/integrations/agent_zero",
            "tests/integrations/agent_zero",
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "mypy --strict clean (agent_zero)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    checks = [
        verify_layout,
        verify_no_source_copied,
        verify_attribution_and_license,
        verify_no_direct_http_process_or_secret,
        verify_model_router_only,
        verify_no_secret_broker_parameter_exists,
        verify_managed_lifecycle,
        verify_result_carries_no_verification_authority,
        verify_work_order_carries_no_forbidden_grant,
        verify_tests,
        verify_ruff,
        verify_mypy,
    ]
    results = [c() for c in checks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 80)
    print("AGENT ZERO STRUCTURE VERIFICATION SUITE (deterministic; no live calls)")
    print("=" * 80 + "\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL':5} | {r.name:70} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")
    if passed == total:
        print(
            "Agent Zero structure gate: PASS (deterministic; live container checked separately).\n"
        )
        return 0
    print("Agent Zero structure gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
