"""Preinstall preparation package (read-only / no host mutation).

Prerequisite manifest, interpreter classification, local-only network policy, phase-order
enforcement, rollback modelling, a dry-run-by-default installer framework, and a source checksum
manifest. Nothing here installs, starts, or mutates a host — it prepares and validates the artifacts
a human operator will use to perform live installation under separate authorization.
"""

from __future__ import annotations

from factory.preinstall.installer import (
    Installer,
    InstallReport,
    InstallStep,
    StepOutcome,
    StepResult,
)
from factory.preinstall.network_policy import (
    HOSTED_EGRESS_DEFAULT_ENABLED,
    NetworkPolicy,
    default_policy,
)
from factory.preinstall.phase_order import (
    LivePhase,
    is_authorization_allowed,
    next_phase,
)
from factory.preinstall.prerequisites import (
    PREREQUISITES,
    Prerequisite,
    evaluate_prerequisite,
    get_prerequisite,
    unmet_mandatory,
)
from factory.preinstall.python_env import (
    PythonKind,
    classify_python,
    linked_sqlite_version,
    remediation_note,
    running_interpreter,
)
from factory.preinstall.rollback import RollbackPlan, Step
from factory.preinstall.source_manifest import (
    MANIFEST_PATH,
    MANIFEST_SOURCES,
    render_manifest,
    validate_manifest,
)

__all__ = [
    "HOSTED_EGRESS_DEFAULT_ENABLED",
    "MANIFEST_PATH",
    "MANIFEST_SOURCES",
    "PREREQUISITES",
    "InstallReport",
    "InstallStep",
    "Installer",
    "LivePhase",
    "NetworkPolicy",
    "Prerequisite",
    "PythonKind",
    "RollbackPlan",
    "Step",
    "StepOutcome",
    "StepResult",
    "classify_python",
    "default_policy",
    "evaluate_prerequisite",
    "get_prerequisite",
    "is_authorization_allowed",
    "linked_sqlite_version",
    "next_phase",
    "remediation_note",
    "render_manifest",
    "running_interpreter",
    "unmet_mandatory",
    "validate_manifest",
]
