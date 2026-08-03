from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _service(name: str) -> dict[str, object]:
    raw = cast(
        dict[str, Any],
        yaml.safe_load(
            (ROOT / "deploy" / "integrations" / name / "compose.yaml").read_text(encoding="utf-8")
        ),
    )
    return cast(dict[str, object], next(iter(raw["services"].values())))


def test_agent_zero_compose_uses_pinned_official_release_and_hardened_boundary() -> None:
    service = _service("agent-zero")
    build = cast(dict[str, Any], service["build"])

    assert build["context"].endswith("#87e1e591e1ba2e8b1a19d34e134fcae490c8dded")
    assert build["dockerfile"] == "docker/run/Dockerfile"
    assert service["image"] == "builder/agent-zero:v2.7-87e1e591"
    assert service["profiles"] == ["builder-enabled"]
    assert service["read_only"] is True
    assert service["privileged"] is False
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert "/var/run/docker.sock" not in str(service)
    assert "OPENAI_API_KEY" not in str(service)
    assert "API_KEY_OPENAI" in cast(dict[str, str], service["environment"])
    assert service["ports"] == ["127.0.0.1:${AGENT_ZERO_PORT:-50080}:80"]


def test_worldmonitor_build_is_commit_pinned_and_hardened() -> None:
    service = _service("worldmonitor")
    build = cast(dict[str, Any], service["build"])

    assert build["args"]["WORLDMONITOR_COMMIT"] == "e51058e1765ef2f0c83ccb1d08d984bc59d23f10"
    assert service["profiles"] == ["builder-enabled"]
    assert service["read_only"] is True
    assert service["privileged"] is False
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["ports"] == ["127.0.0.1:${WORLDMONITOR_PORT:-3000}:3000"]
    dockerfile = (ROOT / "deploy/integrations/worldmonitor/Dockerfile").read_text()
    final_stage = dockerfile.split("FROM node:24.18.0-bookworm-slim")[-1]
    assert "ARG WORLDMONITOR_COMMIT" in final_stage
    assert "LABEL org.opencontainers.image.revision=$WORLDMONITOR_COMMIT" in final_stage


def test_integrations_use_distinct_internal_networks_and_named_data_volumes() -> None:
    agent = _service("agent-zero")
    world = _service("worldmonitor")

    assert agent["networks"] == ["agent-zero-internal"]
    assert world["networks"] == ["worldmonitor-internal"]
    volumes = cast(list[str], agent["volumes"])
    assert any("agent-zero-data:/a0/usr" in item for item in volumes)
    assert all("builder" not in item.lower() for item in volumes)
