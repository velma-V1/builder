#!/usr/bin/env python3
"""Verification suite for the completed preinstallation package (deterministic; no host mutation).

Confirms the preinstall package, docs, and safety guardrails are present and internally consistent:
prerequisite fail-closed evaluation, interpreter classification, local-only network policy (hosted
egress disabled), phase-order enforcement, rollback completeness, the dry-run-by-default installer
(no mutation by default), and the source checksum manifest. Runs NO host probe and installs/starts
NOTHING. Not a phase-promotion gate: PH-4/5/6 remain PENDING / NOT_AUTHORIZED.

Run under the project environment, e.g. ``.venv/bin/python scripts/verify_preinstall_complete.py``.
"""

from __future__ import annotations

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


def verify_package_layout() -> VerificationResult:
    ok, detail = _exists(
        "src/factory/preinstall/__init__.py",
        "src/factory/preinstall/prerequisites.py",
        "src/factory/preinstall/python_env.py",
        "src/factory/preinstall/network_policy.py",
        "src/factory/preinstall/phase_order.py",
        "src/factory/preinstall/rollback.py",
        "src/factory/preinstall/installer.py",
        "src/factory/preinstall/source_manifest.py",
    )
    return VerificationResult("preinstall package present at owner paths", ok, detail)


def verify_prerequisites_fail_closed() -> VerificationResult:
    from factory.livegate.models import CheckStatus
    from factory.preinstall.prerequisites import evaluate_prerequisite, unmet_mandatory

    unknown = evaluate_prerequisite("mystery-tool", (1, 0)) is CheckStatus.ERROR
    below = evaluate_prerequisite("sqlite", (3, 50, 4)) is CheckStatus.FAIL
    ok_all = (
        unmet_mandatory(
            {
                p: (99, 0, 0)
                for p in (
                    "wsl2",
                    "docker",
                    "nvidia_cuda",
                    "ollama",
                    "python",
                    "uv",
                    "sqlite",
                    "git",
                )
            }
        )
        == ()
    )
    ok = unknown and below and ok_all
    return VerificationResult(
        "prerequisites fail closed (unknown->ERROR, below->FAIL)",
        ok,
        f"unknown_error={unknown}; below_fail={below}; all_met_empty={ok_all}",
    )


def verify_python_classification() -> VerificationResult:
    from factory.preinstall.python_env import PythonKind, classify_python

    uv = classify_python("/x/share/uv/python/cpython/bin/python", "") is PythonKind.UV_MANAGED
    distro = classify_python("/usr/bin/python3", "/usr") is PythonKind.DISTRO
    custom = classify_python("/opt/p/bin/python", "/opt/p") is PythonKind.CUSTOM
    ok = uv and distro and custom
    return VerificationResult(
        "interpreter classification (uv/distro/custom)",
        ok,
        f"uv={uv}; distro={distro}; custom={custom}",
    )


def verify_network_policy_local_only() -> VerificationResult:
    from factory.preinstall.network_policy import HOSTED_EGRESS_DEFAULT_ENABLED, default_policy

    policy = default_policy()
    local_ok = policy.evaluate("127.0.0.1")[0] and policy.evaluate("10.0.0.1")[0]
    hosted_denied = policy.evaluate("api.groq.com") == (False, "HOSTED_EGRESS_DISABLED")
    ok = (HOSTED_EGRESS_DEFAULT_ENABLED is False) and local_ok and hosted_denied
    return VerificationResult(
        "local-only network; hosted egress disabled by default",
        ok,
        f"default_disabled={not HOSTED_EGRESS_DEFAULT_ENABLED}",
    )


def verify_phase_order() -> VerificationResult:
    from factory.preinstall.phase_order import LivePhase, is_authorization_allowed, next_phase

    first = next_phase(frozenset()) is LivePhase.PH4
    blocked = not is_authorization_allowed(LivePhase.PH5, frozenset())[0]
    allowed = is_authorization_allowed(LivePhase.PH4, frozenset())[0]
    ok = first and blocked and allowed
    return VerificationResult(
        "phase order PH4->PH5->PH6 enforced",
        ok,
        f"first_ph4={first}; ph5_blocked={blocked}; ph4_ok={allowed}",
    )


def verify_installer_dry_run_default() -> VerificationResult:
    from factory.preinstall.installer import Installer, InstallStep, StepOutcome

    called = {"n": 0}

    def _act() -> None:
        called["n"] += 1

    step = InstallStep("s", "mutate", mutating=True, rollback="undo", action=_act)
    report = Installer("t", (step,)).run()  # default: dry-run
    ok = (
        (not report.mutated)
        and called["n"] == 0
        and (report.results[0].outcome is StepOutcome.SKIPPED_DRY_RUN)
    )
    return VerificationResult(
        "installer is dry-run by default (no mutation)",
        ok,
        f"mutated={report.mutated}; action_calls={called['n']}",
    )


def verify_rollback_completeness() -> VerificationResult:
    from factory.preinstall.rollback import RollbackPlan, Step

    incomplete = RollbackPlan((Step("s", "mutate", mutating=True),))
    complete = RollbackPlan(
        (Step("s", "mutate", mutating=True, rollback="undo", capture_before=True),)
    )
    ok = (not incomplete.is_complete) and complete.is_complete
    return VerificationResult(
        "rollback completeness enforced", ok, f"incomplete_detected={not incomplete.is_complete}"
    )


def verify_source_checksums() -> VerificationResult:
    from factory.preinstall.source_manifest import validate_manifest

    problems = validate_manifest(ROOT)
    return VerificationResult(
        "source checksum manifest validates",
        not problems,
        "ok" if not problems else f"problems={list(problems)}",
    )


def verify_docs_present() -> VerificationResult:
    ok, detail = _exists(
        "docs/preinstall/00-prerequisite-manifest.md",
        "docs/preinstall/01-windows-wsl-layout-and-disk-ports.md",
        "docs/preinstall/02-python-uv-sqlite-plan.md",
        "docs/preinstall/03-docker-compose-topology.md",
        "docs/preinstall/04-nvidia-runtime-plan.md",
        "docs/preinstall/05-ollama-model-roster.md",
        "docs/preinstall/06-local-network-policy.md",
        "docs/preinstall/07-secret-placeholder-procedure.md",
        "docs/preinstall/08-backup-rollback-plan.md",
        "docs/preinstall/09-uninstall-plan.md",
        "docs/preinstall/10-install-order-and-stop-gates.md",
        "docs/live-gate/11-PREINSTALLATION-COMPLETION.md",
        "deploy/preinstall/source-checksums.sha256",
    )
    return VerificationResult("preinstall docs + completion present", ok, detail)


def verify_tests_pass() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/preinstall", "-q"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("preinstall tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/preinstall", "tests/preinstall"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "Ruff clean (preinstall)", result.returncode == 0, f"exit {result.returncode}"
    )


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/preinstall", "tests/preinstall", "--strict"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=900,
    )
    return VerificationResult(
        "mypy --strict clean (preinstall)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    verifications = [
        verify_package_layout,
        verify_prerequisites_fail_closed,
        verify_python_classification,
        verify_network_policy_local_only,
        verify_phase_order,
        verify_installer_dry_run_default,
        verify_rollback_completeness,
        verify_source_checksums,
        verify_docs_present,
        verify_tests_pass,
        verify_ruff,
        verify_mypy,
    ]
    results = [v() for v in verifications]
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print("\n" + "=" * 80)
    print("PREINSTALLATION COMPLETION VERIFICATION SUITE (deterministic; no host mutation)")
    print("=" * 80 + "\n")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{status:5} | {r.name:58} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")

    if passed == total:
        print(
            "Preinstall completion gate: PASS. INSTALLATION_SCRIPTS=PREPARED_NOT_EXECUTED; "
            "PC_IMPLEMENTATION=NOT_STARTED; PH-4/5/6 PENDING; PROM NOT_AUTHORIZED.\n"
        )
        return 0
    print("Preinstall completion gate: INCOMPLETE - fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
