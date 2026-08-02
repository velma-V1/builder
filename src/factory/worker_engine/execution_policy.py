"""The execution-policy boundary (Phase 3B): the sandbox is an optional tool, not a mandatory
environment for every task.

Three explicit execution modes, ordered by how much isolation/control they require:

- ``DIRECT_READ_ONLY`` -- repository inspection, file reading, search, planning, research,
  dependency inspection, diff analysis, and other non-mutating work. No sandbox or worktree is
  ever created; only read-only tools are available.
- ``STAGED_WRITE`` -- the worker proposes file changes without executing risky code. Writes go
  into a controlled staging area (``factory.staging.QuarantinedStaging``), never the live
  repository; an exact change manifest is preserved. Output reaches the live repository only
  through verification, approval, and promotion (Phase 3B's later stages) -- never directly.
- ``SANDBOXED_EXECUTION`` -- running generated/untrusted code, build or test execution that may
  modify the environment, temporary dependency installation, destructive/experimental commands,
  reproducing uncertain failures, or anything else requiring disposable state. A sandbox
  (``factory.worker_engine.workspace.WorkspaceManager``'s git worktree, today) is created only
  when this mode is selected -- never unconditionally, never for every task.

The worker (Agent Zero / Devstral) may *request* a mode as part of its plan, but this module's
``ExecutionPolicy`` makes the final, deterministic decision. Policy can only ever escalate a
request to a *more* isolated mode than requested -- it can never be downgraded below whatever the
deterministic rules require. Every decision (requested mode, selected mode, reason, the specific
rule that fired, and the sandbox/staging identifier if one was created) is persisted for audit --
see ``migrations/runtime/0006_worker_runs.sql``'s ``requested_mode``/``selected_mode``/
``mode_reason``/``policy_rule``/``sandbox_path``/``staging_id`` columns.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ExecutionMode(IntEnum):
    """Ordered by required isolation: a later member is strictly more restrictive/isolated than
    an earlier one. The ``IntEnum`` ordering is what makes "policy can only escalate, never
    downgrade" a simple ``max()`` over this ordinal, not a bespoke comparison table."""

    DIRECT_READ_ONLY = 0
    STAGED_WRITE = 1
    SANDBOXED_EXECUTION = 2

    def __str__(self) -> str:  # readable in persisted records / error messages
        return self.name


class RiskClassification(IntEnum):
    """Deterministic, task/command-level risk tier fed into policy. Not a probability estimate --
    a discrete classification the caller (or a future richer classifier) commits to."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2


#: Command types that always require SANDBOXED_EXECUTION regardless of anything else requested --
#: running code, tests, builds, or installing dependencies are exactly the operations that can
#: mutate the *environment* (not just files), which only a disposable sandbox can safely absorb.
_SANDBOX_REQUIRED_COMMAND_TYPES = frozenset(
    {
        "execute",
        "run_script",
        "run_tests",
        "build",
        "install_dependency",
        "reproduce_failure",
    }
)

_READ_ONLY_POLICY_RULE = "RULE_DEFAULT_READ_ONLY"
_WRITE_INTENT_RULE = "RULE_WRITE_INTENT_REQUIRES_STAGING"
_DEPENDENCY_CHANGE_RULE = "RULE_DEPENDENCY_CHANGE_REQUIRES_SANDBOX"
_HIGH_RISK_RULE = "RULE_HIGH_RISK_REQUIRES_SANDBOX"
_EXECUTABLE_COMMAND_RULE = "RULE_EXECUTABLE_COMMAND_REQUIRES_SANDBOX"
_TASK_POLICY_FLOOR_RULE = "RULE_TASK_POLICY_FLOOR"
_REPOSITORY_POLICY_FLOOR_RULE = "RULE_REPOSITORY_POLICY_FLOOR"


@dataclass(frozen=True, slots=True)
class ExecutionPolicyInput:
    """Everything the policy needs to decide a mode. Every field is deterministic input -- no
    field here is itself a decision (that's ``ExecutionPolicyDecision``'s job)."""

    requested_mode: ExecutionMode
    command_type: str
    write_intent: bool
    dependency_changes: bool
    risk_classification: RiskClassification
    #: An explicit floor set for this specific task (e.g. by an operator/approval scope). ``None``
    #: means no task-specific floor is set.
    task_policy_minimum: ExecutionMode | None = None
    #: A repository-wide floor (e.g. "this repo never allows DIRECT_READ_ONLY to skip staging").
    #: Defaults to the least restrictive floor (no repository-level escalation).
    repository_policy_minimum: ExecutionMode = ExecutionMode.DIRECT_READ_ONLY


@dataclass(frozen=True, slots=True)
class ExecutionPolicyDecision:
    requested_mode: ExecutionMode
    selected_mode: ExecutionMode
    reason: str
    policy_rule: str


def _required_mode_and_rule(policy_input: ExecutionPolicyInput) -> tuple[ExecutionMode, str]:
    """The minimum mode deterministic rules require, and which rule produced it.

    Rules are checked from most to least restrictive; the first one that applies wins, since a
    more restrictive requirement always subsumes a less restrictive one.
    """
    if policy_input.command_type in _SANDBOX_REQUIRED_COMMAND_TYPES:
        return ExecutionMode.SANDBOXED_EXECUTION, _EXECUTABLE_COMMAND_RULE
    if policy_input.risk_classification is RiskClassification.HIGH:
        return ExecutionMode.SANDBOXED_EXECUTION, _HIGH_RISK_RULE
    if policy_input.dependency_changes:
        return ExecutionMode.SANDBOXED_EXECUTION, _DEPENDENCY_CHANGE_RULE
    if policy_input.write_intent:
        return ExecutionMode.STAGED_WRITE, _WRITE_INTENT_RULE
    return ExecutionMode.DIRECT_READ_ONLY, _READ_ONLY_POLICY_RULE


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Deterministic, pure execution-mode decision function. Holds no state; applies nothing."""

    def decide(self, policy_input: ExecutionPolicyInput) -> ExecutionPolicyDecision:
        required_mode, rule = _required_mode_and_rule(policy_input)

        # A task- or repository-level floor can raise the requirement further still, overriding
        # the rule-derived reason/rule when it is the binding constraint.
        if (
            policy_input.task_policy_minimum is not None
            and policy_input.task_policy_minimum > required_mode
        ):
            required_mode, rule = policy_input.task_policy_minimum, _TASK_POLICY_FLOOR_RULE
        if policy_input.repository_policy_minimum > required_mode:
            required_mode, rule = policy_input.repository_policy_minimum, (
                _REPOSITORY_POLICY_FLOOR_RULE
            )

        # The worker's requested mode can only ever push the outcome *up*, never down: taking the
        # max of what was requested and what policy requires is exactly "the worker cannot
        # downgrade a policy-required sandbox operation."
        selected_mode = max(policy_input.requested_mode, required_mode)

        if selected_mode is policy_input.requested_mode and selected_mode is not required_mode:
            # The request already met or exceeded the policy floor -- report the read-only
            # default rule only when nothing more restrictive was ever in play, otherwise credit
            # whichever rule set the floor even though the request already satisfied it.
            reason = (
                f"worker requested {selected_mode}, which already satisfies the "
                f"{rule} floor ({required_mode})"
            )
        elif selected_mode is required_mode and required_mode is not policy_input.requested_mode:
            reason = f"policy escalated {policy_input.requested_mode} to {selected_mode} ({rule})"
        else:
            reason = (
                f"worker requested {selected_mode} and no stricter policy rule applied ({rule})"
            )

        return ExecutionPolicyDecision(
            requested_mode=policy_input.requested_mode,
            selected_mode=selected_mode,
            reason=reason,
            policy_rule=rule,
        )
