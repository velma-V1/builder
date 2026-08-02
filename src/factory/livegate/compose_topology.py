"""Structural validation of **unapplied** Docker Compose templates.

The live sandbox will run workers in an internal-only network with a single dual-homed broker. This
module validates a parsed Compose document against that posture *statically* — it never runs
``docker``, never creates a network, and never starts a container. It is the compile-time twin of
:func:`factory.sandbox.policy.evaluate_spec`: the same ten invariants, expressed over Compose.

A worker service must satisfy all of:

1. attached to exactly one network, and that network is internal;
2. not dual-homed (only the broker may be);
3. no bind mount of a container-runtime socket;
4. no ``network_mode: host``;
5. no published ports;
6. ``read_only: true`` root filesystem;
7. non-root ``user`` (uid != 0);
8. ``cap_drop: [ALL]``;
9. ``security_opt`` contains ``no-new-privileges:true``;
10. bounded CPU / memory / pids limits, all positive.

The broker is exempt from (1)/(2) only: it is the sole service permitted on two networks (one
internal, one egress), and it must still satisfy every other invariant.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

_SOCKET_MARKERS = ("docker.sock", "containerd.sock", "podman.sock")
# A positive quantity: a plain/decimal number with an optional Docker-style unit suffix
# (e.g. ``1.0``, ``512m``, ``2g``, ``1073741824``, ``256``).
_QUANTITY_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*[a-zA-Z]{0,3}\s*$")


@dataclass(frozen=True, slots=True)
class TopologyViolation:
    service: str
    code: str
    detail: str


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_sequence(value: object) -> Sequence[object]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        return ()
    return value


def _internal_networks(doc: Mapping[str, object]) -> frozenset[str]:
    nets = _as_mapping(doc.get("networks"))
    internal: set[str] = set()
    for name, cfg in nets.items():
        cfg_map = _as_mapping(cfg)
        if cfg_map.get("internal") is True:
            internal.add(str(name))
    return frozenset(internal)


def _service_networks(service: Mapping[str, object]) -> tuple[str, ...]:
    nets = service.get("networks")
    if isinstance(nets, Mapping):
        return tuple(str(n) for n in nets)
    if isinstance(nets, Sequence) and not isinstance(nets, str):
        return tuple(str(n) for n in nets)
    return ()


def _is_positive_quantity(value: object) -> bool:
    """True for a positive int/float or a Docker quantity string (``2g``, ``1.0``, ``256``)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        match = _QUANTITY_RE.match(value)
        return match is not None and float(match.group(1)) > 0
    return False


def _check_limits(name: str, service: Mapping[str, object]) -> list[TopologyViolation]:
    deploy = _as_mapping(service.get("deploy"))
    limits = _as_mapping(_as_mapping(deploy.get("resources")).get("limits"))
    # Compose v2 also honours top-level ``cpus`` / ``mem_limit`` / ``pids_limit``.
    cpus = limits.get("cpus", service.get("cpus"))
    memory = limits.get("memory", service.get("mem_limit"))
    pids = limits.get("pids", service.get("pids_limit"))
    out: list[TopologyViolation] = []
    if not _is_positive_quantity(cpus):
        out.append(TopologyViolation(name, "CPU_LIMIT_MISSING", "positive cpus limit required"))
    if not _is_positive_quantity(memory):
        out.append(TopologyViolation(name, "MEM_LIMIT_MISSING", "positive memory limit required"))
    if not _is_positive_quantity(pids):
        out.append(TopologyViolation(name, "PIDS_LIMIT_MISSING", "positive pids limit required"))
    return out


def validate_service(
    name: str,
    service: Mapping[str, object],
    *,
    internal_networks: frozenset[str],
    is_broker: bool = False,
) -> tuple[TopologyViolation, ...]:
    """Validate one service against the hardened topology. Broker relaxes only net invariants."""
    v: list[TopologyViolation] = []
    nets = _service_networks(service)

    if is_broker:
        if len(nets) < 2:
            v.append(
                TopologyViolation(
                    name,
                    "BROKER_NOT_DUAL_HOMED",
                    "broker must bridge an internal and an egress network",
                )
            )
        if not any(n in internal_networks for n in nets):
            v.append(
                TopologyViolation(
                    name, "BROKER_NO_INTERNAL_LEG", "broker must retain one internal-network leg"
                )
            )
    else:
        if len(nets) != 1:
            v.append(
                TopologyViolation(
                    name,
                    "WORKER_NOT_SINGLE_HOMED",
                    f"worker must attach exactly one network, got {list(nets)}",
                )
            )
        if any(n not in internal_networks for n in nets):
            v.append(
                TopologyViolation(
                    name, "WORKER_NET_NOT_INTERNAL", "worker network must be marked internal: true"
                )
            )

    if service.get("network_mode") == "host":
        v.append(TopologyViolation(name, "HOST_NETWORK_DENIED", "network_mode: host is prohibited"))

    for vol in _as_sequence(service.get("volumes")):
        text = vol if isinstance(vol, str) else str(_as_mapping(vol).get("source", ""))
        if any(marker in text for marker in _SOCKET_MARKERS):
            v.append(
                TopologyViolation(
                    name, "RUNTIME_SOCKET_DENIED", f"container-runtime socket mount denied: {text}"
                )
            )

    if _as_sequence(service.get("ports")):
        v.append(
            TopologyViolation(
                name, "PUBLISHED_PORTS_DENIED", "services may not publish ports to the host"
            )
        )

    if service.get("read_only") is not True:
        v.append(TopologyViolation(name, "ROOTFS_NOT_READONLY", "read_only: true is required"))

    user = str(service.get("user", "")).split(":", 1)[0]
    if user in ("", "0", "root"):
        v.append(TopologyViolation(name, "ROOT_USER_DENIED", "a non-root user (uid != 0) required"))

    cap_drop = tuple(str(c).upper() for c in _as_sequence(service.get("cap_drop")))
    if "ALL" not in cap_drop:
        v.append(TopologyViolation(name, "CAPS_NOT_DROPPED", "cap_drop: [ALL] is required"))

    sec_opt = tuple(str(s).replace(" ", "") for s in _as_sequence(service.get("security_opt")))
    if not any(s == "no-new-privileges:true" for s in sec_opt):
        v.append(
            TopologyViolation(
                name, "NO_NEW_PRIVS_MISSING", "security_opt: no-new-privileges:true is required"
            )
        )

    v.extend(_check_limits(name, service))
    return tuple(v)


def validate_compose(
    doc: Mapping[str, object], *, broker_services: frozenset[str] = frozenset()
) -> tuple[TopologyViolation, ...]:
    """Validate every service in a parsed Compose document. Empty result ⇒ topology admissible."""
    internal = _internal_networks(doc)
    services = _as_mapping(doc.get("services"))
    violations: list[TopologyViolation] = []
    if not services:
        return (TopologyViolation("<document>", "NO_SERVICES", "compose defines no services"),)
    broker_seen = False
    for name, service in services.items():
        svc = _as_mapping(service)
        is_broker = str(name) in broker_services
        broker_seen = broker_seen or is_broker
        violations.extend(
            validate_service(str(name), svc, internal_networks=internal, is_broker=is_broker)
        )
    if broker_services and not broker_seen:
        violations.append(
            TopologyViolation("<document>", "BROKER_ABSENT", "declared broker service not found")
        )
    return tuple(violations)
