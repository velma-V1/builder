"""PH-4 / PH-5 / PH-6 live-gate **acceptance matrices**.

Each criterion states an invariant that must be demonstrated *on live infrastructure* before the
corresponding phase may be promoted. Every live criterion has a ``fake_parity`` pointer to the
deterministic test that already proves the same invariant against the fakes — so live integration is
a *confirmation on real components*, not a first test. These matrices are data (rendered into the
evidence docs and checked for completeness); evaluating them requires live infrastructure and is
therefore out of scope for preparation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Phase(StrEnum):
    PH4 = "PH-4"
    PH5 = "PH-5"
    PH6 = "PH-6"


class EvidenceKind(StrEnum):
    RUNTIME_LOG = "runtime_log"
    CONTAINER_INSPECT = "container_inspect"
    LEDGER_QUERY = "ledger_query"
    NETWORK_TRACE = "network_trace"
    REPO_STATE = "repo_state"


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    criterion_id: str
    phase: Phase
    statement: str
    evidence: EvidenceKind
    fake_parity: str
    mandatory: bool = True


PH4_MATRIX: tuple[AcceptanceCriterion, ...] = (
    AcceptanceCriterion(
        "AC4.1",
        Phase.PH4,
        "A real Ollama dispatcher (qwen3:8b) answers a routed request following roster order.",
        EvidenceKind.RUNTIME_LOG,
        "tests/routing/integration :: route order honored",
    ),
    AcceptanceCriterion(
        "AC4.2",
        Phase.PH4,
        "Single-active GPU-heavy reservation serializes concurrent qwen3:14b/aider requests.",
        EvidenceKind.LEDGER_QUERY,
        "tests/routing/unit :: single-active GPU-heavy policy",
    ),
    AcceptanceCriterion(
        "AC4.3",
        Phase.PH4,
        "Quota is charged on every real attempt (success and failure); accounting == ledger.",
        EvidenceKind.LEDGER_QUERY,
        "tests/routing/failure_paths :: all-outcome accounting",
    ),
    AcceptanceCriterion(
        "AC4.4",
        Phase.PH4,
        "No excluded model (glm-4.7) is reachable at runtime; never invoked.",
        EvidenceKind.RUNTIME_LOG,
        "verify_ph4 :: GLM exclusion constant + no leaked route",
    ),
    AcceptanceCriterion(
        "AC4.5",
        Phase.PH4,
        "Fallback selects an approved secondary only; no silent substitution.",
        EvidenceKind.RUNTIME_LOG,
        "verify_ph4 :: explicit-unavailable + approved-only fallback",
    ),
    AcceptanceCriterion(
        "AC4.6",
        Phase.PH4,
        "Kill mid-flight then restart: history rebuilt, sequence advanced, no ID collision.",
        EvidenceKind.LEDGER_QUERY,
        "tests/routing/integration :: restart hardening",
    ),
)

PH5_MATRIX: tuple[AcceptanceCriterion, ...] = (
    AcceptanceCriterion(
        "AC5.1",
        Phase.PH5,
        "A real worker container runs read-only-rootfs, caps-dropped, no-new-privs, non-root.",
        EvidenceKind.CONTAINER_INSPECT,
        "tests/sandbox :: hardened topology weakening denied",
    ),
    AcceptanceCriterion(
        "AC5.2",
        Phase.PH5,
        "An internal-network worker cannot reach the internet; only the broker egresses.",
        EvidenceKind.NETWORK_TRACE,
        "tests/network :: default-deny + broker mediation",
    ),
    AcceptanceCriterion(
        "AC5.3",
        Phase.PH5,
        "Infrastructure destinations are denied unless allow_infrastructure is set.",
        EvidenceKind.NETWORK_TRACE,
        "tests/network :: infrastructure destination denial",
    ),
    AcceptanceCriterion(
        "AC5.4",
        Phase.PH5,
        "Checkpoint commits only owned paths on a real repo; protected-ref writes refused.",
        EvidenceKind.REPO_STATE,
        "tests/git :: owned-path checkpoint + protected-ref guard",
    ),
    AcceptanceCriterion(
        "AC5.5",
        Phase.PH5,
        "Secret broker redacts and revoke-and-forgets against a real secret store.",
        EvidenceKind.RUNTIME_LOG,
        "tests/secret :: redaction + revoke-and-forget + export scan",
    ),
    AcceptanceCriterion(
        "AC5.6",
        Phase.PH5,
        "Live launcher refuses published-ports / runtime-socket / host-network specs.",
        EvidenceKind.CONTAINER_INSPECT,
        "tests/sandbox :: prohibited-privilege denials",
    ),
)

PH6_MATRIX: tuple[AcceptanceCriterion, ...] = (
    AcceptanceCriterion(
        "AC6.1",
        Phase.PH6,
        "Three real workstreams admitted (cap 3) with independence enforced; a 4th is denied.",
        EvidenceKind.RUNTIME_LOG,
        "tests/workstream :: admission cap + independence",
    ),
    AcceptanceCriterion(
        "AC6.2",
        Phase.PH6,
        "Single-writer ownership holds under real concurrency; no lost update.",
        EvidenceKind.LEDGER_QUERY,
        "tests/workstream :: ownership single-writer",
    ),
    AcceptanceCriterion(
        "AC6.3",
        Phase.PH6,
        "Lane state machine drives real tasks; illegal/inconsistent transitions fail closed.",
        EvidenceKind.RUNTIME_LOG,
        "tests/workstream :: lane lifecycle transitions",
    ),
    AcceptanceCriterion(
        "AC6.4",
        Phase.PH6,
        "Conflict detector catches semantic (non-file) conflicts on real branches.",
        EvidenceKind.REPO_STATE,
        "tests/workstream :: conflict detection beyond files",
    ),
    AcceptanceCriterion(
        "AC6.5",
        Phase.PH6,
        "Three real worker failures quarantine the lane; transient failures excluded.",
        EvidenceKind.RUNTIME_LOG,
        "tests/workstream :: 3-failure quarantine",
    ),
    AcceptanceCriterion(
        "AC6.6",
        Phase.PH6,
        "Integration coordinator assigns remediation and never edits source on a real run.",
        EvidenceKind.REPO_STATE,
        "tests/integration :: coordinator never edits source",
    ),
)

ALL_MATRICES: tuple[tuple[Phase, tuple[AcceptanceCriterion, ...]], ...] = (
    (Phase.PH4, PH4_MATRIX),
    (Phase.PH5, PH5_MATRIX),
    (Phase.PH6, PH6_MATRIX),
)


def all_criteria() -> tuple[AcceptanceCriterion, ...]:
    return tuple(c for _, matrix in ALL_MATRICES for c in matrix)
