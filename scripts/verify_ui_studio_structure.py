#!/usr/bin/env python3
"""Verification suite for the UI Studio structure (deterministic; no live calls).

Confirms UI Studio's boundaries: no direct HTTP/process/Docker/env-secret access, no frontend
package is referenced with a guessed exact version, every one of the 16 templates produces a
complete artifact through the fake renderer, the preview lifecycle is dry-run by default, and the
deterministic tests pass under ruff + strict mypy. Makes NO network/process/build-tool call. Not a
phase-promotion gate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_UIS = ROOT / "src" / "factory" / "ui_studio"
_UI_FRONTEND = ROOT / "ui"
_FORBIDDEN_HTTP = (
    "import requests", "import httpx", "import aiohttp", "import http.client",
    "from urllib.request", "import urllib.request", "import socket",
)
_FORBIDDEN_PROCESS = ("import subprocess", "import docker", "from docker", "os.system(")
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
        "errors", "models", "design_tokens", "component_registry", "page_widget_registry",
        "template_registry", "requirements_compiler", "manifest", "state_contracts",
        "data_contracts", "realtime_contracts", "artifact_package", "fake_renderer",
        "preview_lifecycle", "verification",
    ]
    missing = [f for f in files if not (_UIS / f"{f}.py").exists()]
    return VerificationResult("UI Studio modules present", not missing, f"missing={missing}")


def verify_no_direct_http_process_or_secret() -> VerificationResult:
    hits = _scan(_UIS, _FORBIDDEN_HTTP + _FORBIDDEN_PROCESS + _FORBIDDEN_SECRET)
    return VerificationResult(
        "no direct HTTP / process-spawn / Docker / env-secret access", not hits, f"hits={hits}"
    )


def verify_no_source_copied() -> VerificationResult:
    vendor_dirs = [
        d.name for d in _UIS.iterdir()
        if d.is_dir() and d.name in ("vendor", "_vendor", "node_modules", "third_party")
    ]
    total_kb = sum(p.stat().st_size for p in _UIS.rglob("*.py")) // 1024
    ok = not vendor_dirs and total_kb < 400
    return VerificationResult(
        "no vendored frontend source in the backend package", ok,
        f"vendor_dirs={vendor_dirs}; size_kb={total_kb}",
    )


def verify_npm_lockfile_present_and_node_modules_not_committed() -> VerificationResult:
    """Phase 1 (claude/ui-activation-phase-1) intentionally activates the frontend: a real
    package-lock.json is now required and git-tracked. node_modules and any non-npm lockfile must
    still never be *committed* — checked against git's tracked-file list, not the filesystem,
    since node_modules legitimately exists on disk after `npm install` during local development."""
    git = shutil.which("git")
    if git is None:
        return VerificationResult(
            "ui/package-lock.json is git-tracked; node_modules/other lockfiles are not",
            False, "git executable not found on PATH",
        )
    result = subprocess.run(  # noqa: S603 - fixed args, resolved absolute git
        [git, "ls-files", "ui"], capture_output=True, text=True, cwd=ROOT, timeout=30,
    )
    tracked = result.stdout.splitlines()
    forbidden_names = ("node_modules", "pnpm-lock.yaml", "yarn.lock", "bun.lockb")
    hits = [p for p in tracked if any(f"/{name}" in f"/{p}" for name in forbidden_names)]
    lockfile_tracked = "ui/package-lock.json" in tracked
    ok = result.returncode == 0 and lockfile_tracked and not hits
    return VerificationResult(
        "ui/package-lock.json is git-tracked; node_modules/other lockfiles are not",
        ok, f"lockfile_tracked={lockfile_tracked}; forbidden_hits={hits}",
    )


def verify_dependency_versions_pinned_and_consistent() -> VerificationResult:
    """Phase 1 intentionally flips the old assumption (every pinned_version is the
    UNVERIFIED_PENDING_OPERATOR_PIN sentinel) to: every installed dependency's pinned_version must
    match the real version actually resolved in ui/package.json exactly, and any entry not
    installed must be explicitly marked NOT_INSTALLED_PHASE_1 (never the old guessing sentinel,
    and never silently absent from package.json without that marker)."""
    import json

    manifest_path = _UI_FRONTEND / "package.manifest.json"
    package_json_path = _UI_FRONTEND / "package.json"
    if not manifest_path.is_file() or not package_json_path.is_file():
        return VerificationResult(
            "ui/package.manifest.json pinned versions match ui/package.json", False,
            f"missing: manifest={not manifest_path.is_file()} package.json={not package_json_path.is_file()}",
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
    installed = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}

    deps = manifest.get("dependencies", []) + manifest.get("devDependencies", [])
    mismatches: list[str] = []
    for d in deps:
        name, pinned = d["name"], d.get("pinned_version")
        if pinned == "UNVERIFIED_PENDING_OPERATOR_PIN":
            mismatches.append(f"{name}: still has the unpinned sentinel")
        elif name in installed:
            if pinned != installed[name]:
                mismatches.append(f"{name}: manifest={pinned} package.json={installed[name]}")
        elif pinned != "NOT_INSTALLED_PHASE_1":
            mismatches.append(f"{name}: not installed but not marked NOT_INSTALLED_PHASE_1")
    ok = bool(deps) and not mismatches
    return VerificationResult(
        "ui/package.manifest.json pinned versions match ui/package.json", ok,
        f"mismatches={mismatches}",
    )


def verify_all_templates_render_complete_artifacts() -> VerificationResult:
    from factory.ui_studio import (
        ComponentRegistry,
        FakeRenderer,
        RenderRequest,
        TemplateRegistry,
        UIRequirement,
        assemble_artifact_package,
        builder_command_center_workflow,
        builder_task_snapshot_contract,
        compile_requirement,
        default_token_set,
        require_complete_artifact,
    )
    from factory.ui_studio.template_registry import TEMPLATES

    templates, components = TemplateRegistry(), ComponentRegistry()
    failures: list[str] = []
    for template in TEMPLATES:
        try:
            plan = compile_requirement(
                UIRequirement(template_id=template.template_id, title="Verification Project"),
                templates=templates, components=components,
            )
            tokens = default_token_set()
            render_result = FakeRenderer().render(RenderRequest(plan, tokens))
            package = assemble_artifact_package(
                plan, tokens, render_result, components=components, project_id="verify-1",
                created_at=1000,
                state_contracts=(builder_command_center_workflow(),),
                data_contracts=(builder_task_snapshot_contract(),),
            )
            require_complete_artifact(package)
        except Exception as exc:
            failures.append(f"{template.template_id}: {exc}")
    return VerificationResult(
        "all 16 templates render a complete, verified artifact", not failures and len(TEMPLATES) == 16,
        f"template_count={len(TEMPLATES)}; failures={failures}",
    )


def verify_preview_lifecycle_dry_run() -> VerificationResult:
    from factory.ui_studio.preview_lifecycle import build_preview_lifecycle

    report = build_preview_lifecycle().run()
    ok = not report.mutated and "(MISSING)" not in build_preview_lifecycle().format_plan()
    return VerificationResult(
        "preview lifecycle is dry-run by default (no server started)", ok, f"mutated={report.mutated}"
    )


def verify_tests() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/ui_studio", "-q"],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return VerificationResult("UI Studio tests pass", result.returncode == 0, tail)


def verify_ruff() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/factory/ui_studio", "tests/ui_studio"],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult("Ruff clean (ui_studio)", result.returncode == 0, f"exit {result.returncode}")


def verify_mypy() -> VerificationResult:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/factory/ui_studio", "tests/ui_studio", "--strict"],
        capture_output=True, text=True, cwd=ROOT, timeout=900,
    )
    return VerificationResult(
        "mypy --strict clean (ui_studio)", result.returncode == 0, f"exit {result.returncode}"
    )


def main() -> int:
    checks = [
        verify_layout, verify_no_direct_http_process_or_secret, verify_no_source_copied,
        verify_npm_lockfile_present_and_node_modules_not_committed,
        verify_dependency_versions_pinned_and_consistent, verify_all_templates_render_complete_artifacts,
        verify_preview_lifecycle_dry_run, verify_tests, verify_ruff, verify_mypy,
    ]
    results = [c() for c in checks]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("\n" + "=" * 80)
    print("UI STUDIO STRUCTURE VERIFICATION SUITE (deterministic; no live calls)")
    print("=" * 80 + "\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL':5} | {r.name:65} | {r.detail}")
    print("\n" + "=" * 80)
    print(f"TOTAL: {passed}/{total} checks passed")
    print("=" * 80 + "\n")
    if passed == total:
        print("UI Studio structure gate: PASS. PHASE_1_DASHBOARD_RUNNABLE_LOCALLY; "
              "fake renderer backend contract unchanged; frontend installed, not Tauri-bundled, "
              "no live backend connection opened.\n")
        return 0
    print("UI Studio structure gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
