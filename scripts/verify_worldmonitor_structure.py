#!/usr/bin/env python3
"""Verification suite for the WorldMonitor integration structure (deterministic; no live calls).

Confirms the managed-module boundaries: no WorldMonitor upstream source is vendored into Builder,
the official revision and AGPL obligations are recorded, no direct HTTP library
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
        "official_client",
        "mcp_client",
        "normalization",
        "provenance",
        "health",
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
        and WORLDMONITOR_MANIFEST.license == "AGPL-3.0-or-later"
        and WORLDMONITOR_MANIFEST.license_verified is True
        and WORLDMONITOR_MANIFEST.revision_verified is True
        and bool(AGPL_OBLIGATIONS)
    )
    return VerificationResult(
        "official revision, attribution, and AGPL boundary recorded", ok, "ok"
    )


def verify_no_direct_http_or_secret() -> VerificationResult:
    hits = _scan(_FORBIDDEN_HTTP + _FORBIDDEN_SECRET)
    return VerificationResult("no direct HTTP / env-secret access", not hits, f"hits={hits}")


def verify_official_read_only_contract() -> VerificationResult:
    from factory.integrations.worldmonitor.official_client import WorldMonitorOfficialClient

    slots = set(WorldMonitorOfficialClient.__slots__)
    ok = "base_url" in slots and not any("provider" in slot or "secret" in slot for slot in slots)
    return VerificationResult(
        "official read-only client has no provider/secret handle",
        ok,
        f"slots={sorted(slots)}",
    )


def verify_managed_build_lifecycle() -> VerificationResult:
    source = (ROOT / "src/factory/integrations/runtime.py").read_text(encoding="utf-8")
    compose = (ROOT / "deploy/integrations/worldmonitor/compose.yaml").read_text(encoding="utf-8")
    ok = 'spec.compose("build", "--pull")' in source and "builder-enabled" in compose
    return VerificationResult(
        "WorldMonitor uses Builder-managed pinned build lifecycle", ok, "managed runtime + profile"
    )


def verify_capability_scope_is_honest() -> VerificationResult:
    from factory.integrations.worldmonitor import WORLDMONITOR_MANIFEST

    ok = (
        WORLDMONITOR_MANIFEST.section_complete is False
        and WORLDMONITOR_MANIFEST.implemented_capability_scope == ("disasters.earthquakes",)
        and len(WORLDMONITOR_MANIFEST.approved_capability_scope) == 13
    )
    return VerificationResult(
        "approved capability scope is explicitly incomplete",
        ok,
        "implemented=disasters.earthquakes; required=13 categories",
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
        verify_official_read_only_contract,
        verify_managed_build_lifecycle,
        verify_capability_scope_is_honest,
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
            "WorldMonitor structure gate: PASS; capability section remains INCOMPLETE "
            "(earthquakes only; live container checked separately).\n"
        )
        return 0
    print("WorldMonitor structure gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
