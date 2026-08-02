#!/usr/bin/env python3
"""Verification suite for the hosted provider adapters (deterministic; no live calls).

Confirms the provider adapters are structurally safe and fail-closed: no direct HTTP library inside
adapters (all network via the brokered transport), no environment/secret access outside the
SecretBroker, the Provider enum is extended without dropping existing values, hosted egress is
disabled by default, and the deterministic provider tests pass under ruff + strict mypy. Makes NO
network call and reads NO credentials. Not a phase-promotion gate.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PROVIDERS = ROOT / "src" / "factory" / "providers"
_FORBIDDEN_HTTP = (
    "import requests",
    "import httpx",
    "import aiohttp",
    "import http.client",
    "from urllib.request",
    "import urllib.request",
    "urllib.request.urlopen",
    "import socket",
)
_FORBIDDEN_SECRET = ("os.environ", "os.getenv", "getenv(")


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str


def _scan(directory: Path, needles: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for path in sorted(directory.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}::{needle}")
    return hits


def verify_layout() -> VerificationResult:
    files = [
        "errors",
        "transport",
        "models",
        "brokered",
        "openai_core",
        "hosted",
        "openrouter",
        "huggingface",
        "together",
        "replicate",
        "registry",
    ]
    missing = [f for f in files if not (_PROVIDERS / f"{f}.py").exists()]
    return VerificationResult("provider modules present", not missing, f"missing={missing}")


def verify_no_direct_http() -> VerificationResult:
    hits = _scan(_PROVIDERS, _FORBIDDEN_HTTP)
    return VerificationResult(
        "no direct HTTP library inside adapters (broker-only)", not hits, f"hits={hits}"
    )


def verify_no_env_secret_access() -> VerificationResult:
    hits = _scan(_PROVIDERS, _FORBIDDEN_SECRET)
    return VerificationResult(
        "no environment/secret access outside SecretBroker", not hits, f"hits={hits}"
    )


def verify_provider_enum() -> VerificationResult:
    from factory.routing.models import Provider

    names = {p.name for p in Provider}
    added = {"OPENROUTER", "HUGGING_FACE", "TOGETHER", "REPLICATE"}
    preserved = {"OLLAMA", "AIDER", "GROQ", "CEREBRAS", "NVIDIA"}
    ok = added <= names and preserved <= names
    return VerificationResult(
        "Provider enum extended, existing preserved", ok, f"names={sorted(names)}"
    )


def verify_brokered_usage() -> VerificationResult:
    # Each hosted adapter path must go through BrokeredHttp (the security envelope).
    brokered = "BrokeredHttp" in (_PROVIDERS / "hosted.py").read_text(encoding="utf-8")
    brokered_repl = "BrokeredHttp" in (_PROVIDERS / "replicate.py").read_text(encoding="utf-8")
    ok = brokered and brokered_repl
    return VerificationResult("adapters route through the brokered envelope", ok, f"ok={ok}")


def verify_hosted_egress_disabled() -> VerificationResult:
    from factory.preinstall.network_policy import HOSTED_EGRESS_DEFAULT_ENABLED

    ok = HOSTED_EGRESS_DEFAULT_ENABLED is False
    return VerificationResult("hosted egress disabled by default", ok, f"default={not ok}")


def verify_tests() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/providers", "-q"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("provider tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/providers", "tests/providers"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "Ruff clean (providers)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/providers", "tests/providers", "--strict"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "mypy --strict clean (providers)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    checks = [
        verify_layout,
        verify_no_direct_http,
        verify_no_env_secret_access,
        verify_provider_enum,
        verify_brokered_usage,
        verify_hosted_egress_disabled,
        verify_tests,
        verify_ruff,
        verify_mypy,
    ]
    results = [c() for c in checks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 80)
    print("PROVIDER ADAPTERS VERIFICATION SUITE (deterministic; no live calls)")
    print("=" * 80 + "\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL':5} | {r.name:56} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")
    if passed == total:
        print(
            "Provider adapters gate: PASS. BUILT_NOT_ACTIVATED; keys NOT_PROVISIONED; "
            "no live calls; hosted egress DISABLED.\n"
        )
        return 0
    print("Provider adapters gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
