"""Agent Zero integration — Builder-managed external worker contracts.

Agent Zero is an **external, pinned dependency** (its source is not copied into Builder) integrated
strictly as a **managed worker**. Builder remains the sole authority for task state, repositories,
branches, models, tools, network, secrets, permissions, approvals, verification, promotion, and
scheduling. Agent Zero may only execute an assigned work order, use explicitly granted tools,
produce patches/artifacts, stream visible progress, and return evidence. It never receives a
provider API key, a Docker socket, unrestricted host filesystem access, direct ``main`` access,
merge/approval/promotion/self-update authority, or hidden scheduling — and its own claim of success
is never Builder's verification verdict. **All AI is routed by the Builder router.** Runtime
installation and lifecycle are owned by :mod:`factory.integrations.runtime`.
"""

from __future__ import annotations

from factory.integrations.agent_zero.adapter import AgentZeroAdapter
from factory.integrations.agent_zero.capabilities import CapabilitySet, require_tool
from factory.integrations.agent_zero.compatibility import check_compatibility
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.event_validation import (
    ValidatedEventStream,
    validate_event_stream,
)
from factory.integrations.agent_zero.fake_transport import (
    FakeAgentZeroTransport,
    ScriptedRun,
    event,
    full_failure_stream,
    full_success_stream,
    sample_work_order,
)
from factory.integrations.agent_zero.health import DEFAULT_UNAVAILABLE_AFTER_FAILURES, check_health
from factory.integrations.agent_zero.manifest import (
    AGENT_ZERO_MANIFEST,
    MANAGED_WORKER_OBLIGATIONS,
    AgentZeroManifest,
)
from factory.integrations.agent_zero.models import (
    AgentZeroEvent,
    AgentZeroEventType,
    AgentZeroIntegrationMode,
    AgentZeroResult,
    Artifact,
    CompatibilityReport,
    EvidenceBundle,
    EvidenceItem,
    ModuleHealth,
    ModuleHealthState,
    Patch,
    ResourceEnvelope,
    ToolGrant,
    WorkerOutcome,
    WorkOrder,
    content_digest,
)
from factory.integrations.agent_zero.policy import (
    AgentZeroCapabilityRequest,
    AgentZeroModelResult,
    AgentZeroNetworkPolicy,
    BrokeredAgentZeroHttp,
    ModelRouterPort,
    assert_no_self_certification,
    assert_no_self_promotion,
    deny_direct_main_access,
    deny_hidden_scheduling,
    enforce_sandbox_boundary,
    evaluate_output_path,
)
from factory.integrations.agent_zero.provenance import ProvenanceStep, build_provenance
from factory.integrations.agent_zero.result_mapping import map_events_to_result
from factory.integrations.agent_zero.task_mapping import build_work_order
from factory.integrations.agent_zero.transport import (
    AgentZeroTransport,
    TransportFailure,
    TransportTimeout,
)

__all__ = [
    "AGENT_ZERO_MANIFEST",
    "DEFAULT_UNAVAILABLE_AFTER_FAILURES",
    "MANAGED_WORKER_OBLIGATIONS",
    "AgentZeroAdapter",
    "AgentZeroCapabilityRequest",
    "AgentZeroError",
    "AgentZeroErrorCode",
    "AgentZeroEvent",
    "AgentZeroEventType",
    "AgentZeroIntegrationMode",
    "AgentZeroManifest",
    "AgentZeroModelResult",
    "AgentZeroNetworkPolicy",
    "AgentZeroResult",
    "AgentZeroTransport",
    "Artifact",
    "BrokeredAgentZeroHttp",
    "CapabilitySet",
    "CompatibilityReport",
    "EvidenceBundle",
    "EvidenceItem",
    "FakeAgentZeroTransport",
    "ModelRouterPort",
    "ModuleHealth",
    "ModuleHealthState",
    "Patch",
    "ProvenanceStep",
    "ResourceEnvelope",
    "ScriptedRun",
    "ToolGrant",
    "TransportFailure",
    "TransportTimeout",
    "ValidatedEventStream",
    "WorkOrder",
    "WorkerOutcome",
    "assert_no_self_certification",
    "assert_no_self_promotion",
    "build_provenance",
    "build_work_order",
    "check_compatibility",
    "check_health",
    "content_digest",
    "deny_direct_main_access",
    "deny_hidden_scheduling",
    "enforce_sandbox_boundary",
    "evaluate_output_path",
    "event",
    "full_failure_stream",
    "full_success_stream",
    "map_events_to_result",
    "require_tool",
    "sample_work_order",
    "validate_event_stream",
]
