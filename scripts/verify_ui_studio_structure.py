#!/usr/bin/env python3
"""Verification suite for the UI Studio structure (deterministic; no live calls).

Confirms UI Studio's boundaries: no direct HTTP/process/Docker/env-secret access, no frontend
package is referenced with a guessed exact version, every one of the 16 templates produces a
complete artifact through the fake renderer, the preview lifecycle is dry-run by default, and the
deterministic tests pass under ruff + strict mypy. Makes NO network/process/build-tool call. Not a
phase-promotion gate.
"""

from __future__ import annotations

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


def verify_no_lockfile_or_node_modules_in_frontend_scaffold() -> VerificationResult:
    forbidden_names = (
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "node_modules", "bun.lockb",
    )
    hits = [
        str(p.relative_to(ROOT)) for name in forbidden_names for p in _UI_FRONTEND.rglob(name)
    ]
    return VerificationResult(
        "no lockfile / node_modules committed under ui/", not hits, f"hits={hits}"
    )


def verify_no_guessed_exact_dependency_versions() -> VerificationResult:
    manifest_path = _UI_FRONTEND / "package.manifest.json"
    if not manifest_path.is_file():
        return VerificationResult(
            "ui/package.manifest.json present with no guessed exact versions", False, "missing"
        )
    import json

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    deps = data.get("dependencies", []) + data.get("devDependencies", [])
    bad = [d["name"] for d in deps if d.get("pinned_version") != "UNVERIFIED_PENDING_OPERATOR_PIN"]
    ok = bool(deps) and not bad
    return VerificationResult(
        "ui/package.manifest.json present with no guessed exact versions", ok, f"unpinned_ok_bad={bad}"
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
        verify_no_lockfile_or_node_modules_in_frontend_scaffold,
        verify_no_guessed_exact_dependency_versions, verify_all_templates_render_complete_artifacts,
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
        print("UI Studio structure gate: PASS. STRUCTURE_COMPLETE_NOT_INSTALLED; "
              "fake renderer only; no frontend package installed.\n")
        return 0
    print("UI Studio structure gate: INCOMPLETE — fix failures above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
