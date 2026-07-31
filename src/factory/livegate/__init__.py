"""Stage-3 live-gate **preparation** package.

Read-only readiness modelling, structural validators, live-adapter/durable-store contracts, and
acceptance matrices. Nothing here installs, starts, configures, or activates anything — it prepares
the artifacts a human operator will use to authorize and later perform live integration.
"""

from __future__ import annotations

from factory.livegate.acceptance import (
    ALL_MATRICES,
    AcceptanceCriterion,
    EvidenceKind,
    Phase,
    all_criteria,
)
from factory.livegate.adapter_contracts import (
    LIVE_ADAPTER_OBLIGATIONS,
    LiveAdapterObligation,
    structural_parity_violations,
)
from factory.livegate.compose_topology import (
    TopologyViolation,
    validate_compose,
    validate_service,
)
from factory.livegate.durable_schema import (
    DURABLE_SCHEMA_MANIFEST,
    SchemaPin,
    validate_manifest,
)
from factory.livegate.models import CheckStatus, ReadinessCheck, ReadinessReport
from factory.livegate.redaction import redact_pairs, redact_text
from factory.livegate.sqlite_compliance import (
    SQLITE_GATE_ID,
    durable_activation_fails_closed_below_floor,
    evaluate_sqlite_compliance,
)
from factory.livegate.version_probe import (
    APPROVED_LOCAL_MODELS,
    evaluate_docker,
    evaluate_nvidia,
    evaluate_ollama_models,
    evaluate_wsl,
    parse_docker_version,
    parse_nvidia_smi,
    parse_ollama_list,
)

__all__ = [
    "ALL_MATRICES",
    "APPROVED_LOCAL_MODELS",
    "DURABLE_SCHEMA_MANIFEST",
    "LIVE_ADAPTER_OBLIGATIONS",
    "SQLITE_GATE_ID",
    "AcceptanceCriterion",
    "CheckStatus",
    "EvidenceKind",
    "LiveAdapterObligation",
    "Phase",
    "ReadinessCheck",
    "ReadinessReport",
    "SchemaPin",
    "TopologyViolation",
    "all_criteria",
    "durable_activation_fails_closed_below_floor",
    "evaluate_docker",
    "evaluate_nvidia",
    "evaluate_ollama_models",
    "evaluate_sqlite_compliance",
    "evaluate_wsl",
    "parse_docker_version",
    "parse_nvidia_smi",
    "parse_ollama_list",
    "redact_pairs",
    "redact_text",
    "structural_parity_violations",
    "validate_compose",
    "validate_manifest",
    "validate_service",
]
