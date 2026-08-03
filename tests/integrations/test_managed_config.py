from pathlib import Path

import pytest

from scripts._config import load_config


def _write_config(path: Path, *, agent_enabled: str = "true") -> None:
    path.write_text(
        f"""
wsl:
  distribution: Ubuntu
repository:
  path: {path.parent}
database:
  path: runtime.db
ports:
  read_api: 8000
  orchestrator_api: 8100
  dashboard: 1420
browser:
  auto_open: false
integrations:
  state_path: integrations.db
  agent_zero:
    enabled: {agent_enabled}
    release: v2.7
    commit: 87e1e591e1ba2e8b1a19d34e134fcae490c8dded
    image: agent0ai/agent-zero:v2.7
    port: 50080
    cpu_millis: 2000
    memory_mb: 4096
    timeout_s: 900
  worldmonitor:
    enabled: true
    release: v2.5.23
    commit: e51058e1765ef2f0c83ccb1d08d984bc59d23f10
    source: https://github.com/koala73/worldmonitor.git
    port: 3000
    cpu_millis: 1000
    memory_mb: 2048
    timeout_s: 120
""".lstrip(),
        encoding="utf-8",
    )


def test_load_config_exposes_pinned_managed_integrations(tmp_path: Path) -> None:
    config_path = tmp_path / "builder.yaml"
    _write_config(config_path)

    config = load_config(config_path)

    assert config.integrations is not None
    assert config.integrations.state_path == tmp_path / "integrations.db"
    assert config.integrations.agent_zero.release == "v2.7"
    assert config.integrations.agent_zero.commit == "87e1e591e1ba2e8b1a19d34e134fcae490c8dded"
    assert config.integrations.worldmonitor.release == "v2.5.23"
    assert config.integrations.worldmonitor.port == 3000


def test_load_config_rejects_conflicting_integration_ports(tmp_path: Path) -> None:
    config_path = tmp_path / "builder.yaml"
    _write_config(config_path)
    text = config_path.read_text(encoding="utf-8").replace("port: 3000", "port: 50080")
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="ports must be unique"):
        load_config(config_path)


def test_load_config_rejects_unpinned_revision(tmp_path: Path) -> None:
    config_path = tmp_path / "builder.yaml"
    _write_config(config_path)
    text = config_path.read_text(encoding="utf-8").replace(
        "87e1e591e1ba2e8b1a19d34e134fcae490c8dded", "main"
    )
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="40-character commit"):
        load_config(config_path)


def test_load_config_requires_boolean_enabled_value(tmp_path: Path) -> None:
    config_path = tmp_path / "builder.yaml"
    _write_config(config_path, agent_enabled="yes please")

    with pytest.raises(ValueError, match="enabled must be a boolean"):
        load_config(config_path)
