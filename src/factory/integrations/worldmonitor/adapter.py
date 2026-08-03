"""WorldMonitorAdapter — the Builder-side managed interface to the WorldMonitor module.

Read-only data access (brokered), capability-gated, normalized to provenance-preserving records.
**All AI goes through the Builder router** (:class:`ModelRouterPort`) — WorldMonitor never selects a
provider, loads a model, calls Ollama/cloud, or holds credentials. It never certifies output
and never edits the roster.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from factory.integrations.worldmonitor.capabilities import CapabilitySet, require_capability
from factory.integrations.worldmonitor.errors import WorldMonitorError
from factory.integrations.worldmonitor.health import check_health
from factory.integrations.worldmonitor.models import (
    Category,
    IntelligenceRecord,
    WorldMonitorHealth,
    WorldMonitorMode,
    WorldMonitorQuery,
    WorldMonitorResult,
    WorldMonitorViewCommand,
)
from factory.integrations.worldmonitor.normalization import deduplicate, normalize_record
from factory.integrations.worldmonitor.policy import (
    AiCapabilityRequest,
    AiResult,
    BrokeredWorldMonitorHttp,
    ModelRouterPort,
)
from factory.integrations.worldmonitor.rest_client import WorldMonitorRestClient
from factory.integrations.worldmonitor.retention import DEFAULT_RETENTION, RetentionPolicy
from factory.integrations.worldmonitor.ui_bridge import UiMessage, validate_ui_message
from factory.routing.models import Privacy


class WorldMonitorAdapter:
    __slots__ = (
        "_allowed_ui_origins",
        "_approved_source_domains",
        "_base_url",
        "_brokered",
        "_capabilities",
        "_clock",
        "_mode",
        "_rest",
        "_retention",
        "_router",
        "_workspace_url",
    )

    def __init__(
        self,
        *,
        mode: WorldMonitorMode,
        base_url: str,
        brokered: BrokeredWorldMonitorHttp,
        capabilities: CapabilitySet,
        model_router: ModelRouterPort,
        approved_source_domains: frozenset[str],
        retention: RetentionPolicy = DEFAULT_RETENTION,
        workspace_url: str = "",
        allowed_ui_origins: frozenset[str] = frozenset(),
        clock: Callable[[], int],
    ) -> None:
        self._mode = mode
        self._brokered = brokered
        self._base_url = base_url
        self._rest = WorldMonitorRestClient(brokered, base_url)
        self._capabilities = capabilities
        self._router = model_router
        self._approved_source_domains = approved_source_domains
        self._retention = retention
        self._workspace_url = workspace_url
        self._allowed_ui_origins = allowed_ui_origins
        self._clock = clock

    def probe(self) -> WorldMonitorHealth:
        return check_health(self._brokered, self._base_url, self._clock())

    def health(self) -> WorldMonitorHealth:
        return self.probe()

    def discover_capabilities(self) -> CapabilitySet:
        return self._capabilities

    def cancel(self) -> bool:
        return False

    def get_workspace_url(self) -> str:
        return self._workspace_url

    def validate_view_command(self, message: UiMessage) -> WorldMonitorViewCommand:
        return validate_ui_message(message, allowed_origins=self._allowed_ui_origins)

    def normalize(self, raw: Mapping[str, object], category: Category) -> IntelligenceRecord:
        return normalize_record(
            raw,
            category=category,
            now=self._clock(),
            ttl_s=self._retention.normalized_ttl_s,
            approved_source_domains=self._approved_source_domains,
        )

    def query(self, query: WorldMonitorQuery) -> WorldMonitorResult:
        try:
            require_capability(self._capabilities, query.category)
            raw = self._rest.fetch(query.category)
            records = tuple(self.normalize(item, query.category) for item in raw)
            records = deduplicate(records)[: query.limit]
            return WorldMonitorResult(query, records)
        except WorldMonitorError as exc:
            return WorldMonitorResult(
                query, error_code=exc.code.value, reason=self._brokered.redact(exc.detail)
            )

    def request_ai(
        self, task_id: str, capability: str, prompt: str, *, privacy: Privacy = Privacy.LOCAL_ONLY
    ) -> AiResult:
        """The ONLY way WorldMonitor obtains AI: hand a capability request to the Builder router."""
        return self._router.request(
            AiCapabilityRequest(
                task_id=task_id,
                capability=capability,
                prompt=prompt,
                privacy=privacy,
            )
        )
