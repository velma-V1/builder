from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"blocker_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_section2_history_gate_uses_reachable_scoped_history() -> None:
    module = _load_script("verify_section2")
    result = module.verify_git_commits()
    assert result.passed, result.detail
    assert "scoped boundary commits in reachable history" in result.detail


def test_rph3_manifest_declares_every_current_sql_migration() -> None:
    module = _load_script("verify_roadmap_ph3")
    declared = set(module.MIGRATION_SHA256)
    current = {
        path.relative_to(ROOT).as_posix()
        for migration_root in ("audit", "runtime", "security")
        for path in (ROOT / "migrations" / migration_root).glob("*.sql")
    }
    assert declared == current
    result = module.verify_migration_manifest()
    assert result.passed, result.detail
