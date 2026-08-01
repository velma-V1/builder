"""Shared config loader for Builder's launcher (Phase 3A).

Reads ``config/builder.yaml`` — the single source of truth for launcher-consumed settings —
so no path/port/toggle is hardcoded independently in more than one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "builder.yaml"


@dataclass(frozen=True, slots=True)
class BuilderConfig:
    wsl_distribution: str
    repository_path: Path
    database_path: Path
    read_api_port: int
    orchestrator_api_port: int
    dashboard_port: int
    browser_auto_open: bool


def load_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> BuilderConfig:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    repository_path = Path(raw["repository"]["path"])
    database_path = Path(raw["database"]["path"])
    if not database_path.is_absolute():
        database_path = repository_path / database_path

    return BuilderConfig(
        wsl_distribution=raw["wsl"]["distribution"],
        repository_path=repository_path,
        database_path=database_path,
        read_api_port=int(raw["ports"]["read_api"]),
        orchestrator_api_port=int(raw["ports"]["orchestrator_api"]),
        dashboard_port=int(raw["ports"]["dashboard"]),
        browser_auto_open=bool(raw["browser"]["auto_open"]),
    )
