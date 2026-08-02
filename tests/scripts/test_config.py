"""Phase 3A — scripts/_config.py: load_config() reads config/builder.yaml correctly.

Uses the real PyYAML parser (unlike scripts/windows/Builder.ps1's regex extraction, which has
its own dedicated tests in test_windows_shortcut.py) -- comments in the file are handled
natively and correctly here, with no special-casing needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_CONFIG_PATH = _REPO_ROOT / "config" / "builder.yaml"


def _load_script(name: str) -> ModuleType:
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass string-annotation resolution needs this
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def config_module() -> ModuleType:
    return _load_script("_config")


def test_load_config_reads_the_real_config_file(config_module: ModuleType) -> None:
    config = config_module.load_config(_REAL_CONFIG_PATH)
    assert config.wsl_distribution == "Ubuntu"
    assert config.repository_path == Path("/home/xxthatguyxx/builder")
    assert config.database_path == Path("/home/xxthatguyxx/builder/runtime.db")
    assert config.read_api_port == 8000
    assert config.orchestrator_api_port == 8100
    assert config.dashboard_port == 1420
    assert config.browser_auto_open is True


def test_load_config_resolves_relative_database_path_against_repository_path(
    config_module: ModuleType, tmp_path: Path
) -> None:
    config_path = tmp_path / "builder.yaml"
    config_path.write_text(
        "wsl:\n"
        "  distribution: TestDistro\n"
        "repository:\n"
        "  path: /some/repo\n"
        "database:\n"
        "  path: relative.db\n"
        "ports:\n"
        "  read_api: 1\n"
        "  orchestrator_api: 2\n"
        "  dashboard: 3\n"
        "browser:\n"
        "  auto_open: false\n"
    )
    config = config_module.load_config(config_path)
    assert config.database_path == Path("/some/repo/relative.db")
    assert config.browser_auto_open is False


def test_load_config_keeps_absolute_database_path_as_is(
    config_module: ModuleType, tmp_path: Path
) -> None:
    config_path = tmp_path / "builder.yaml"
    config_path.write_text(
        "wsl:\n"
        "  distribution: TestDistro\n"
        "repository:\n"
        "  path: /some/repo\n"
        "database:\n"
        "  path: /elsewhere/runtime.db\n"
        "ports:\n"
        "  read_api: 1\n"
        "  orchestrator_api: 2\n"
        "  dashboard: 3\n"
        "browser:\n"
        "  auto_open: true\n"
    )
    config = config_module.load_config(config_path)
    assert config.database_path == Path("/elsewhere/runtime.db")
