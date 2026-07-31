"""WorldMonitor REST client (brokered; read-only fetches only).

Uses the official pinned OpenAPI when available. When it is not verifiable, the client uses an
interface + fixtures and is marked BLOCKED_UNVERIFIED (no fabricated schema). All fetches are
read-only and go through the brokered envelope.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.integrations.worldmonitor.models import Category
from factory.integrations.worldmonitor.policy import BrokeredWorldMonitorHttp

#: Until the upstream OpenAPI spec is verified (source + digest), the generated client is blocked.
OPENAPI_CLIENT_STATUS = "BLOCKED_UNVERIFIED"

#: Category → documented read-only path (interface-level; confirmed against the pinned spec later).
_PATHS: dict[Category, str] = {
    Category.WORLD_BRIEF: "/v1/world-brief",
    Category.COUNTRY_RISK: "/v1/country-risk",
    Category.CONFLICT_EVENTS: "/v1/conflict-events",
    Category.MILITARY_ACTIVITY: "/v1/military-activity",
    Category.CYBER_THREATS: "/v1/cyber-threats",
    Category.DISASTERS: "/v1/disasters",
    Category.CLIMATE: "/v1/climate",
    Category.MARITIME: "/v1/maritime",
    Category.AVIATION: "/v1/aviation",
    Category.MARKETS: "/v1/markets",
    Category.ECONOMIC_INDICATORS: "/v1/economic-indicators",
    Category.INFRASTRUCTURE: "/v1/infrastructure",
    Category.NEWS_RESEARCH: "/v1/news",
}


class WorldMonitorRestClient:
    __slots__ = ("_base_url", "_brokered")

    def __init__(self, brokered: BrokeredWorldMonitorHttp, base_url: str) -> None:
        self._brokered = brokered
        self._base_url = base_url

    def fetch(self, category: Category) -> tuple[Mapping[str, object], ...]:
        """Read-only fetch of raw records for a category. Malformed payloads fail closed."""
        path = _PATHS.get(category)
        if path is None:
            raise WorldMonitorError(
                WorldMonitorErrorCode.CAPABILITY_UNAVAILABLE,
                f"no documented path for {category.value}",
            )
        response = self._brokered.request("GET", f"{self._base_url}{path}")
        if response.status != 200:
            raise WorldMonitorError(
                WorldMonitorErrorCode.UNAVAILABLE, f"fetch HTTP {response.status}"
            )
        try:
            data = json.loads(response.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorldMonitorError(
                WorldMonitorErrorCode.MALFORMED_RESPONSE, self._brokered.redact(str(exc))
            ) from exc
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            raise WorldMonitorError(
                WorldMonitorErrorCode.MALFORMED_RESPONSE, "missing records array"
            )
        return tuple(r for r in records if isinstance(r, dict))
