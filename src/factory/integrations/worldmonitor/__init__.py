"""WorldMonitor integration — managed first-class module (STRUCTURE_COMPLETE_NOT_INSTALLED).

WorldMonitor is an **external, pinned dependency** (its source is not copied into Builder). This
package is the Builder-side managed interface: brokered read-only data access, capability discovery,
normalization with preserved provenance, an MCP discovery seam, a UI workspace contract, a dry-run
lifecycle, and retention policy. **All AI is routed by the Builder router** — WorldMonitor never
selects a provider or holds credentials. Nothing here connects, installs, or activates anything.
"""

from __future__ import annotations

from factory.integrations.worldmonitor.adapter import WorldMonitorAdapter
from factory.integrations.worldmonitor.capabilities import CapabilitySet, require_capability
from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.integrations.worldmonitor.health import check_health
from factory.integrations.worldmonitor.lifecycle import (
    FUTURE_ISOLATION,
    LIFECYCLE_PHASES,
    FutureIsolation,
    build_lifecycle,
)
from factory.integrations.worldmonitor.manifest import (
    AGPL_OBLIGATIONS,
    WORLDMONITOR_MANIFEST,
    WorldMonitorManifest,
)
from factory.integrations.worldmonitor.mcp_client import (
    FakeMcpTransport,
    McpServerCard,
    McpTransport,
    discovered_tools,
)
from factory.integrations.worldmonitor.models import (
    Category,
    Freshness,
    HealthState,
    IntelligenceRecord,
    WorldMonitorCapability,
    WorldMonitorEvent,
    WorldMonitorFreshness,
    WorldMonitorHealth,
    WorldMonitorMode,
    WorldMonitorQuery,
    WorldMonitorResult,
    WorldMonitorSourceRef,
    WorldMonitorViewCommand,
    WorldMonitorWorkspaceState,
)
from factory.integrations.worldmonitor.normalization import deduplicate, normalize_record
from factory.integrations.worldmonitor.policy import (
    AiCapabilityRequest,
    AiResult,
    BrokeredWorldMonitorHttp,
    ModelRouterPort,
    WorldMonitorNetworkPolicy,
)
from factory.integrations.worldmonitor.rest_client import (
    OPENAPI_CLIENT_STATUS,
    WorldMonitorRestClient,
)
from factory.integrations.worldmonitor.retention import DEFAULT_RETENTION, RetentionPolicy
from factory.integrations.worldmonitor.ui_bridge import (
    SUPPORTED_MESSAGE_VERSION,
    UiMessage,
    validate_ui_message,
)

__all__ = [
    "AGPL_OBLIGATIONS",
    "DEFAULT_RETENTION",
    "FUTURE_ISOLATION",
    "LIFECYCLE_PHASES",
    "OPENAPI_CLIENT_STATUS",
    "SUPPORTED_MESSAGE_VERSION",
    "WORLDMONITOR_MANIFEST",
    "AiCapabilityRequest",
    "AiResult",
    "BrokeredWorldMonitorHttp",
    "CapabilitySet",
    "Category",
    "FakeMcpTransport",
    "Freshness",
    "FutureIsolation",
    "HealthState",
    "IntelligenceRecord",
    "McpServerCard",
    "McpTransport",
    "ModelRouterPort",
    "RetentionPolicy",
    "UiMessage",
    "WorldMonitorAdapter",
    "WorldMonitorCapability",
    "WorldMonitorError",
    "WorldMonitorErrorCode",
    "WorldMonitorEvent",
    "WorldMonitorFreshness",
    "WorldMonitorHealth",
    "WorldMonitorManifest",
    "WorldMonitorMode",
    "WorldMonitorNetworkPolicy",
    "WorldMonitorQuery",
    "WorldMonitorRestClient",
    "WorldMonitorResult",
    "WorldMonitorSourceRef",
    "WorldMonitorViewCommand",
    "WorldMonitorWorkspaceState",
    "build_lifecycle",
    "check_health",
    "deduplicate",
    "discovered_tools",
    "normalize_record",
    "require_capability",
    "validate_ui_message",
]
