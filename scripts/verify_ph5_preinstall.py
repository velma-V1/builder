#!/usr/bin/env python3
"""Verification suite for PH-5 (Section 5) — Git, Worktree & Sandbox Isolation (preinstallation).

Scoped gate for the PH-5 preinstallation isolation core: real Git on temporary repositories plus
deterministic fake sandbox / secret / network backends and pure-logic cache / staging. It is NOT a
phase-promotion gate and makes NO live-runtime claim: real WSL2/Docker execution, live container
identity/mount/network-namespace validation, live secret injection, and live resource enforcement
remain LIVE_SANDBOX_PENDING (see docs/verification/ph5-pending-live-gate-register.md).

Run under the project environment, e.g. ``.venv/bin/python scripts/verify_ph5_preinstall.py``.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
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
        "src/factory/git/manager.py",
        "src/factory/sandbox/fake_backend.py",
        "src/factory/sandbox/policy.py",
        "src/factory/secret/fake_backend.py",
        "src/factory/network/fake_backend.py",
        "src/factory/cache/store.py",
        "src/factory/staging/manager.py",
    )
    return VerificationResult("PH-5 modules live at their plan-assigned owner paths", ok, detail)


def verify_git_policy_on_real_repo() -> VerificationResult:
    from factory.git import CommitTrailers, GitManager, VerificationStatus
    from factory.git.errors import GitError

    gm = GitManager()
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / "proj"
        gm.init_repo(repo)
        base = gm.head_commit(repo)
        gm.create_task_branch(repo, base, task_id="T1", stage_id="S1")
        (repo / "src").mkdir()
        (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        trailers = CommitTrailers("T1", "S1", "W1", "CP1", VerificationStatus.CHECKPOINT)
        gm.checkpoint(repo, task_id="T1", owned_paths=("src/**",), subject="a", trailers=trailers)
        checks = []
        try:
            gm.guard_protected_ref("main")
        except GitError as exc:
            checks.append(exc.code == "PROTECTED_REF_WRITE" and exc.security)
        try:
            gm.guard_no_force_push(force=True)
        except GitError as exc:
            checks.append(exc.code == "FORCE_PUSH_DENIED")
        (repo / "outside.py").write_text("y = 2\n", encoding="utf-8")
        try:
            gm.checkpoint(repo, task_id="T1", owned_paths=("src/**",), subject="x", trailers=trailers)
        except GitError as exc:
            checks.append(exc.code == "CHECKPOINT_SCOPE" and exc.security)
    ok = len(checks) == 3 and all(checks)
    return VerificationResult(
        "Git: protected-ref + force-push + owned-path checkpoint enforced (real repo)", ok,
        f"guards={checks}",
    )


def verify_sandbox_isolation_policy() -> VerificationResult:
    from factory.sandbox import (
        FakeWslDockerBackend,
        ResourceLimits,
        SandboxError,
        SandboxSpec,
        SandboxStatus,
    )

    limits = ResourceLimits(1000, 2048, 4096, 128, 600)
    backend = FakeWslDockerBackend()
    clean = backend.provision(
        SandboxSpec("T1", "W1", "img", "v1", resources=limits)
    )
    non_root = clean.identity is not None and clean.identity.uid != 0
    denied = []
    for flag in ("windows_native", "privileged", "host_docker_socket", "run_as_root"):
        try:
            backend.provision(SandboxSpec("T1", "W1", "img", "v1", resources=limits, **{flag: True}))
        except SandboxError as exc:
            denied.append(exc.code == "SANDBOX_POLICY_DENIED")
    unavailable = FakeWslDockerBackend(available=False).provision(
        SandboxSpec("T1", "W1", "img", "v1", resources=limits)
    )
    ok = (
        clean.status is SandboxStatus.PROVISIONED
        and non_root
        and len(denied) == 4
        and all(denied)
        and unavailable.status is SandboxStatus.RUNTIME_UNAVAILABLE
    )
    return VerificationResult(
        "Sandbox: non-root default, prohibited privileges denied, explicit unavailable", ok,
        f"non_root={non_root}; denied={denied}; unavailable={unavailable.status.value}",
    )


def verify_secret_lifecycle() -> VerificationResult:
    from factory.secret import FakeSecretBackend, SecretError, SecretRef

    b = FakeSecretBackend({"r1": "s3cr3t"})
    b.inject(SecretRef("r1", "TOKEN", "T1", 100), now=0)
    redacted = "s3cr3t" not in b.redact("value s3cr3t", now=1)
    b.revoke_task("T1")
    forgotten = not b.has_persisted_material(now=2)
    blocked = False
    try:
        b.scan_export("leak s3cr3t")
    except SecretError as exc:
        blocked = exc.code == "SECRET_IN_EXPORT"
    ok = redacted and forgotten and blocked
    return VerificationResult(
        "Secret: redaction + revoke-and-forget + export scan", ok,
        f"redacted={redacted}; forgotten={forgotten}; export_blocked={blocked}",
    )


def verify_network_default_deny() -> VerificationResult:
    from factory.network import Direction, FakeNetworkBackend, NetworkApproval, NetworkRequest

    b = FakeNetworkBackend()
    approval = NetworkApproval(
        "A1", "T1", frozenset({"example.com"}), frozenset({"https"}), frozenset({"GET"}), 100, 1000
    )
    default_deny = not b.evaluate(None, NetworkRequest("example.com", "https", "GET"), now=0).allowed
    allowed = b.evaluate(approval, NetworkRequest("example.com", "https", "GET"), now=0).allowed
    redirect_contained = not b.evaluate_redirect(approval, "evil.com", now=0).allowed
    inbound = not b.evaluate(
        approval, NetworkRequest("example.com", "https", "GET", Direction.INBOUND), now=0
    ).allowed
    ok = default_deny and allowed and redirect_contained and inbound
    return VerificationResult(
        "Network: default-deny, allowlist, redirect containment, no inbound", ok,
        f"deny={default_deny}; allow={allowed}; redirect={redirect_contained}; inbound_denied={inbound}",
    )


def verify_cache_and_staging() -> VerificationResult:
    from factory.cache import CacheError, CacheScope, ContentAddressedCache
    from factory.staging import QuarantinedStaging, StagedFile, StagingError

    cache = ContentAddressedCache()
    k1 = cache.put(CacheScope.SANDBOX, "s1", b"bytes")
    k2 = cache.put(CacheScope.SANDBOX, "s2", b"bytes")
    scoped = k1 != k2 and k1.content_hash == k2.content_hash
    cred_blocked = False
    try:
        cache.put(CacheScope.SANDBOX, "s1", b"tok=s3cr3t", forbidden_values=["s3cr3t"])
    except CacheError as exc:
        cred_blocked = exc.code == "CACHE_CREDENTIAL"

    with tempfile.TemporaryDirectory() as d:
        stg = QuarantinedStaging("stg-1", Path(d), approved_scope=("src/**",))
        stg.stage(StagedFile("src/a.py", b"x = 1\n", "sbx"))
        unauth_blocked = False
        try:
            stg.promote(authorized=False)
        except StagingError as exc:
            unauth_blocked = exc.code == "PROMOTION_UNAUTHORIZED"
        promoted = stg.promote(authorized=True).promoted
    ok = scoped and cred_blocked and unauth_blocked and promoted
    return VerificationResult(
        "Cache scoping/credential-free + staging inspection/authorization gate", ok,
        f"scoped={scoped}; cred_blocked={cred_blocked}; unauth={unauth_blocked}; promoted={promoted}",
    )


def verify_tests_pass_with_coverage() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/git", "tests/sandbox", "tests/secret",
            "tests/network", "tests/cache", "tests/staging", "-q",
            "--cov=src/factory/git", "--cov=src/factory/sandbox", "--cov=src/factory/secret",
            "--cov=src/factory/network", "--cov=src/factory/cache", "--cov=src/factory/staging",
            "--cov-branch", "--cov-fail-under=95",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    summary = (result.stdout.strip().split("\n") or ["?"])[-1]
    return VerificationResult(
        "PH-5 tests pass with >=95% branch coverage", result.returncode == 0,
        f"exit {result.returncode}; {summary}",
    )


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "ruff", "check",
            "src/factory/git", "src/factory/sandbox", "src/factory/secret",
            "src/factory/network", "src/factory/cache", "src/factory/staging",
            "tests/git", "tests/sandbox", "tests/secret",
            "tests/network", "tests/cache", "tests/staging",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("Ruff clean (PH-5 src + tests)", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy",
            "src/factory/git", "src/factory/sandbox", "src/factory/secret",
            "src/factory/network", "src/factory/cache", "src/factory/staging",
            "tests/git", "tests/sandbox", "tests/secret",
            "tests/network", "tests/cache", "tests/staging", "--strict",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("mypy --strict clean (PH-5)", result.returncode == 0, f"exit {result.returncode}")


def verify_evidence_present() -> VerificationResult:
    ok, detail = _exists(
        "docs/verification/ph5-preinstall-evidence.md",
        "docs/verification/ph5-requirement-to-test-matrix.md",
        "docs/verification/ph5-failure-path-matrix.md",
        "docs/verification/ph5-pending-live-gate-register.md",
    )
    return VerificationResult("PH-5 evidence package present", ok, detail)


def main() -> int:
    verifications = [
        verify_owned_path_layout,
        verify_git_policy_on_real_repo,
        verify_sandbox_isolation_policy,
        verify_secret_lifecycle,
        verify_network_default_deny,
        verify_cache_and_staging,
        verify_tests_pass_with_coverage,
        verify_ruff,
        verify_mypy,
        verify_evidence_present,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("PH-5 PREINSTALLATION VERIFICATION SUITE — Git, Worktree & Sandbox Isolation")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:64} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print("PH-5 preinstallation gate: PASS. LIVE_SANDBOX_PENDING; not a phase promotion.\n")
        return 0
    print("PH-5 preinstallation gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
