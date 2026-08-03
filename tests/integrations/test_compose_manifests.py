from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _compose(name: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        yaml.safe_load(
            (ROOT / "deploy" / "integrations" / name / "compose.yaml").read_text(encoding="utf-8")
        ),
    )


def _service(name: str, service: str | None = None) -> dict[str, object]:
    services = cast(dict[str, Any], _compose(name)["services"])
    if service is None:
        return cast(dict[str, object], next(iter(services.values())))
    return cast(dict[str, object], services[service])


def test_agent_zero_compose_uses_pinned_official_release_and_hardened_boundary() -> None:
    service = _service("agent-zero")
    build = cast(dict[str, Any], service["build"])

    assert build["context"] == "../../.."
    assert build["dockerfile"] == "deploy/integrations/agent-zero/Dockerfile.api"
    assert build["args"]["BASE_IMAGE"] == "builder/agent-zero-parent:404177ac"
    labels = cast(dict[str, str], build["labels"])
    assert labels["org.opencontainers.image.revision"] == "87e1e591e1ba2e8b1a19d34e134fcae490c8dded"
    assert (
        labels["org.opencontainers.image.base.digest"]
        == "sha256:404177ac27f283ffcbd843ec590fbb3f5e375a746b8157137fd26dcb9d6fd192"
    )
    assert service["image"] == "builder/agent-zero-api:v2.7-87e1e591"
    assert service["profiles"] == ["builder-enabled"]
    assert service["read_only"] is True
    assert service["privileged"] is False
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert "/var/run/docker.sock" not in str(service)
    assert "OPENAI_API_KEY" not in str(service)
    assert "API_KEY_OPENAI" in cast(dict[str, str], service["environment"])
    assert "ports" not in service
    healthcheck = " ".join(cast(list[str], service["healthcheck"]["test"]))
    assert "http://127.0.0.1:8080/api/health" in healthcheck

    dockerfile = (ROOT / "deploy/integrations/agent-zero/Dockerfile.api").read_text(
        encoding="utf-8"
    )
    assert "ARG BASE_IMAGE=builder/agent-zero-parent:404177ac" in dockerfile
    assert 'CMD ["/opt/venv-a0/bin/python", "/a0/run_ui.py", "--dockerized=true"]' in dockerfile
    assert "ENTRYPOINT []" in dockerfile


def test_agent_zero_two_relay_ingress_topology() -> None:
    agent = _service("agent-zero", "agent-zero")
    relay = _service("agent-zero", "agent-zero-bridge-relay")
    ingress = _service("agent-zero", "agent-zero-ingress")
    egress = _service("agent-zero", "agent-zero-egress")
    networks = cast(dict[str, Any], _compose("agent-zero")["networks"])

    assert agent["networks"] == ["agent-zero-internal"]
    assert "ports" not in agent
    assert relay["image"].startswith("alpine/socat@sha256:e7b17711")
    assert relay["networks"] == ["agent-zero-loopback", "agent-zero-internal"]
    assert "ports" not in relay
    assert relay["command"] == ["TCP-LISTEN:8080,fork,reuseaddr", "TCP:builder-agent-zero:8080"]
    assert ingress["image"].startswith("alpine/socat@sha256:e7b17711")
    assert ingress["networks"] == ["agent-zero-loopback"]
    assert ingress["ports"] == ["127.0.0.1:${AGENT_ZERO_PORT:-50080}:8080"]
    assert ingress["command"] == [
        "TCP-LISTEN:8080,fork,reuseaddr",
        "TCP:agent-zero-bridge-relay:8080",
    ]

    for svc in (agent, relay, ingress):
        assert svc["user"] == "1000:1000"
        assert svc["read_only"] is True
        assert svc["privileged"] is False
        assert svc["cap_drop"] == ["ALL"]
        assert svc["security_opt"] == ["no-new-privileges:true"]
        assert "/var/run/docker.sock" not in str(svc)

    assert networks["agent-zero-internal"] == {"internal": True}
    assert networks["agent-zero-loopback"] == {"internal": False}
    assert "agent-zero-gateway" in networks
    assert "agent-zero-loopback" not in egress["networks"]


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
