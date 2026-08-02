"""Derive an :class:`ExecutionPolicyInput` from a task's human-submitted description
(``factory.orchestrator.models.TaskRequestRecord.description``).

This is a deliberately simple, documented, deterministic heuristic -- not a model call. The
operator/task description may include explicit structured hints (each on its own line, matched
case-insensitively):

    mode: sandboxed_execution
    command: run_tests
    write_intent: true
    dependency_changes: true
    risk: high

Any hint not present falls back to a conservative default (read-only, low risk, no write/
dependency intent) -- the execution policy in ``execution_policy.py`` is what actually decides
the mode from this input, and it can only ever escalate a request, never rely on this classifier
alone to grant a permissive mode.
"""

from __future__ import annotations

import re

from factory.worker_engine.execution_policy import (
    ExecutionMode,
    ExecutionPolicyInput,
    RiskClassification,
)

_HINT_RE = re.compile(r"(?im)^\s*(\w+)\s*:\s*(\S.*?)\s*$")

_MODE_NAMES = {mode.name.lower(): mode for mode in ExecutionMode}
_RISK_NAMES = {risk.name.lower(): risk for risk in RiskClassification}
_TRUTHY = frozenset({"true", "1", "yes"})


def classify_task_description(
    description: str,
    *,
    repository_policy_minimum: ExecutionMode = ExecutionMode.DIRECT_READ_ONLY,
) -> ExecutionPolicyInput:
    hints: dict[str, str] = {}
    for match in _HINT_RE.finditer(description):
        key, value = match.group(1).lower(), match.group(2).strip()
        if key in {"mode", "command", "write_intent", "dependency_changes", "risk"}:
            hints[key] = value

    requested_mode = _MODE_NAMES.get(hints.get("mode", "").lower(), ExecutionMode.DIRECT_READ_ONLY)
    risk = _RISK_NAMES.get(hints.get("risk", "").lower(), RiskClassification.LOW)
    write_intent = hints.get("write_intent", "").lower() in _TRUTHY
    dependency_changes = hints.get("dependency_changes", "").lower() in _TRUTHY
    command_type = hints.get("command", "read_file")

    return ExecutionPolicyInput(
        requested_mode=requested_mode,
        command_type=command_type,
        write_intent=write_intent,
        dependency_changes=dependency_changes,
        risk_classification=risk,
        repository_policy_minimum=repository_policy_minimum,
    )
