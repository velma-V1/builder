"""Stage-3 unit — structural validation of the unapplied Compose templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from factory.livegate.compose_topology import validate_compose, validate_service

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_DIR = ROOT / "deploy" / "compose"

_INTERNAL = frozenset({"factory-internal"})


def _worker(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "image": "factory/worker:sha256-abc",
        "networks": ["factory-internal"],
        "read_only": True,
        "user": "1000:1000",
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "pids_limit": 256,
        "mem_limit": "2g",
        "cpus": 1.0,
    }
    base.update(over)
    return base


def test_clean_worker_has_no_violations() -> None:
    assert validate_service("w", _worker(), internal_networks=_INTERNAL) == ()


@pytest.mark.parametrize(
    ("over", "code"),
    [
        ({"networks": ["factory-internal", "factory-egress"]}, "WORKER_NOT_SINGLE_HOMED"),
        ({"networks": ["public"]}, "WORKER_NET_NOT_INTERNAL"),
        ({"network_mode": "host"}, "HOST_NETWORK_DENIED"),
        ({"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}, "RUNTIME_SOCKET_DENIED"),
        ({"ports": ["8080:8080"]}, "PUBLISHED_PORTS_DENIED"),
        ({"read_only": False}, "ROOTFS_NOT_READONLY"),
        ({"user": "0:0"}, "ROOT_USER_DENIED"),
        ({"user": "root"}, "ROOT_USER_DENIED"),
        ({"cap_drop": []}, "CAPS_NOT_DROPPED"),
        ({"security_opt": []}, "NO_NEW_PRIVS_MISSING"),
        ({"pids_limit": 0}, "PIDS_LIMIT_MISSING"),
        ({"mem_limit": 0}, "MEM_LIMIT_MISSING"),
        ({"cpus": 0}, "CPU_LIMIT_MISSING"),
    ],
)
def test_each_weakening_is_detected(over: dict[str, object], code: str) -> None:
    codes = {v.code for v in validate_service("w", _worker(**over), internal_networks=_INTERNAL)}
    assert code in codes


def test_broker_may_be_dual_homed_worker_may_not() -> None:
    broker = _worker(networks=["factory-internal", "factory-egress"])
    assert validate_service("broker", broker, internal_networks=_INTERNAL, is_broker=True) == ()
    # A single-homed "broker" is missing its egress leg.
    lone = _worker(networks=["factory-internal"])
    violations = validate_service("b", lone, internal_networks=_INTERNAL, is_broker=True)
    assert "BROKER_NOT_DUAL_HOMED" in {v.code for v in violations}


def test_document_with_no_services_flagged() -> None:
    codes = {v.code for v in validate_compose({"services": {}})}
    assert "NO_SERVICES" in codes


def test_declared_broker_absent_flagged() -> None:
    doc = {"networks": {"factory-internal": {"internal": True}},
           "services": {"w": _worker()}}
    codes = {v.code for v in validate_compose(doc, broker_services=frozenset({"broker"}))}
    assert "BROKER_ABSENT" in codes


def _load(name: str) -> dict[str, object]:
    data: Any = yaml.safe_load((COMPOSE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_shipped_worker_template_is_clean() -> None:
    assert validate_compose(_load("factory-workers.compose.yaml")) == ()


def test_shipped_broker_template_is_clean() -> None:
    doc = _load("factory-broker.compose.yaml")
    assert validate_compose(doc, broker_services=frozenset({"broker"})) == ()
