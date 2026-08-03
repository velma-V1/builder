"""Shared config loader for Builder's launcher (Phase 3A).

Reads ``config/builder.yaml`` — the single source of truth for launcher-consumed settings —
so no path/port/toggle is hardcoded independently in more than one place.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "builder.yaml"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class ManagedIntegrationConfig:
    enabled: bool
    release: str
    commit: str
    port: int
    cpu_millis: int
    memory_mb: int
    timeout_s: int
    image: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class IntegrationsConfig:
    state_path: Path
    agent_zero: ManagedIntegrationConfig
    worldmonitor: ManagedIntegrationConfig


@dataclass(frozen=True, slots=True)
class BuilderConfig:
    wsl_distribution: str
    repository_path: Path
    database_path: Path
    read_api_port: int
    orchestrator_api_port: int
    dashboard_port: int
    browser_auto_open: bool
    integrations: IntegrationsConfig | None = None


def _integration_config(name: str, raw: object) -> ManagedIntegrationConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"integrations.{name} must be an object")
    enabled = raw.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError(f"integrations.{name}.enabled must be a boolean")
    commit = raw.get("commit")
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        raise ValueError(f"integrations.{name}.commit must be a 40-character commit")
    release = raw.get("release")
    if not isinstance(release, str) or not release.strip():
        raise ValueError(f"integrations.{name}.release must be non-empty")
    port = int(raw.get("port", 0))
    cpu_millis = int(raw.get("cpu_millis", 0))
    memory_mb = int(raw.get("memory_mb", 0))
    timeout_s = int(raw.get("timeout_s", 0))
    if not 1 <= port <= 65535:
        raise ValueError(f"integrations.{name}.port must be a valid TCP port")
    if min(cpu_millis, memory_mb, timeout_s) <= 0:
        raise ValueError(f"integrations.{name} resource limits must be positive")
    image = raw.get("image")
    source = raw.get("source")
    if image is not None and not isinstance(image, str):
        raise ValueError(f"integrations.{name}.image must be a string")
    if source is not None and not isinstance(source, str):
        raise ValueError(f"integrations.{name}.source must be a string")
    return ManagedIntegrationConfig(
        enabled=enabled,
        release=release,
        commit=commit,
        port=port,
        cpu_millis=cpu_millis,
        memory_mb=memory_mb,
        timeout_s=timeout_s,
        image=image,
        source=source,
    )


def load_config(config_path: Path = _DEFAULT_CONFIG_PATH) -> BuilderConfig:
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    repository_path = Path(raw["repository"]["path"])
    database_path = Path(raw["database"]["path"])
    if not database_path.is_absolute():
        database_path = repository_path / database_path
    integrations_raw = raw.get("integrations")
    integrations = None
    reserved_ports = {
        int(raw["ports"]["read_api"]),
        int(raw["ports"]["orchestrator_api"]),
        int(raw["ports"]["dashboard"]),
    }
    if integrations_raw is not None:
        if not isinstance(integrations_raw, dict):
            raise ValueError("integrations configuration must be an object")
        agent_zero = _integration_config("agent_zero", integrations_raw.get("agent_zero"))
        worldmonitor = _integration_config("worldmonitor", integrations_raw.get("worldmonitor"))
        integration_ports = {agent_zero.port, worldmonitor.port}
        if len(integration_ports) != 2 or reserved_ports & integration_ports:
            raise ValueError("Builder and integration ports must be unique")
        state_path = Path(str(integrations_raw.get("state_path", "integrations.db")))
        if not state_path.is_absolute():
            state_path = repository_path / state_path
        integrations = IntegrationsConfig(state_path, agent_zero, worldmonitor)

    return BuilderConfig(
        wsl_distribution=raw["wsl"]["distribution"],
        repository_path=repository_path,
        database_path=database_path,
        read_api_port=int(raw["ports"]["read_api"]),
        orchestrator_api_port=int(raw["ports"]["orchestrator_api"]),
        dashboard_port=int(raw["ports"]["dashboard"]),
        browser_auto_open=bool(raw["browser"]["auto_open"]),
        integrations=integrations,
    )
