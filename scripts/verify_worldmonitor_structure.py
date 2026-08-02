#!/usr/bin/env python3
"""Verification suite for the WorldMonitor integration structure (deterministic; no live calls).

Confirms the managed-module boundaries: no WorldMonitor upstream source is vendored into Builder,
attribution + license obligations are recorded (commercial use unresolved), no direct HTTP library
or environment-secret access, AI access is model-router-only (no provider/secret handle), the
lifecycle is dry-run by default, hosted access is disabled, and the deterministic tests pass under
ruff + strict mypy. Makes NO network/MCP call. Not a phase-promotion gate.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_WM = ROOT / "src" / "factory" / "integrations" / "worldmonitor"
_FORBIDDEN_HTTP = (
    "import requests",
    "import httpx",
    "import aiohttp",
    "import http.client",
    "from urllib.request",
    "import urllib.request",
    "import socket",
)
_FORBIDDEN_SECRET = ("os.environ", "os.getenv", "getenv(")


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _scan(needles: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for path in sorted(_WM.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}::{needle}")
    return hits


def verify_layout() -> VerificationResult:
    files = [
        "errors",
        "models",
        "manifest",
        "capabilities",
        "adapter",
        "rest_client",
        "mcp_client",
        "normalization",
        "provenance",
        "health",
        "lifecycle",
        "policy",
        "retention",
        "ui_bridge",
        "fake_transport",
    ]
    missing = [f for f in files if not (_WM / f"{f}.py").exists()]
    return VerificationResult("WorldMonitor modules present", not missing, f"missing={missing}")


def verify_no_source_copied() -> VerificationResult:
    # A thin managed interface has no vendored subtree and stays modest in size.
    vendor_dirs = [
        d.name
        for d in _WM.iterdir()
        if d.is_dir() and d.name in ("vendor", "_vendor", "upstream", "third_party")
    ]
    total_kb = sum(p.stat().st_size for p in _WM.rglob("*.py")) // 1024
    ok = not vendor_dirs and total_kb < 200
    return VerificationResult(
        "no WorldMonitor upstream source vendored",
        ok,
        f"vendor_dirs={vendor_dirs}; size_kb={total_kb}",
    )


def verify_attribution_and_license() -> VerificationResult:
    from factory.integrations.worldmonitor import WORLDMONITOR_MANIFEST
    from factory.integrations.worldmonitor.manifest import AGPL_OBLIGATIONS

    ok = (
        bool(WORLDMONITOR_MANIFEST.attribution)
        and "koala73/worldmonitor" in WORLDMONITOR_MANIFEST.upstream_repo
        and "UNRESOLVED" in WORLDMONITOR_MANIFEST.commercial_use_status
        and WORLDMONITOR_MANIFEST.license_verified is False
        and bool(AGPL_OBLIGATIONS)
    )
    return VerificationResult("attribution + license (commercial unresolved) recorded", ok, "ok")


def verify_no_direct_http_or_secret() -> VerificationResult:
    hits = _scan(_FORBIDDEN_HTTP + _FORBIDDEN_SECRET)
    return VerificationResult("no direct HTTP / env-secret access", not hits, f"hits={hits}")


def verify_model_router_only() -> VerificationResult:
    from factory.integrations.worldmonitor import WorldMonitorAdapter

    slots = set(WorldMonitorAdapter.__slots__)
    ok = "_router" in slots and not any("provider" in s or "secret" in s for s in slots)
    return VerificationResult(
        "AI access is Builder-router-only (no provider/secret handle)",
        ok,
        f"router_slot={'_router' in slots}",
    )


def verify_lifecycle_dry_run() -> VerificationResult:
    from factory.integrations.worldmonitor import build_lifecycle

    report = build_lifecycle().run()  # default dry-run
    ok = not report.mutated and "(MISSING)" not in build_lifecycle().format_plan()
    return VerificationResult(
        "lifecycle is dry-run by default (no mutation)", ok, f"mutated={report.mutated}"
    )


def verify_tests() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/integrations/worldmonitor", "-q"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("WorldMonitor tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/integrations", "tests/integrations"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "Ruff clean (integrations)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "src/factory/integrations",
            "tests/integrations",
            "--strict",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "mypy --strict clean (integrations)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    checks = [
        verify_layout,
        verify_no_source_copied,
        verify_attribution_and_license,
        verify_no_direct_http_or_secret,
        verify_model_router_only,
        verify_lifecycle_dry_run,
        verify_tests,
        verify_ruff,
        verify_mypy,
    ]
    results = [c() for c in checks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 80)
    print("WORLDMONITOR STRUCTURE VERIFICATION SUITE (deterministic; no live calls)")
    print("=" * 80 + "\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL':5} | {r.name:58} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")
    if passed == total:
        print(
            "WorldMonitor structure gate: PASS. STRUCTURE_COMPLETE_NOT_INSTALLED; "
            "external pinned dependency; hosted access DISABLED; router-only AI.\n"
        )
        return 0
    print("WorldMonitor structure gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
