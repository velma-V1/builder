"""Typed client for WorldMonitor v2.5.23's pinned SeBuf seismology contract."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

from factory.integrations.worldmonitor.errors import WorldMonitorError
from factory.integrations.worldmonitor.models import Category, IntelligenceRecord
from factory.integrations.worldmonitor.normalization import normalize_record
from factory.providers.transport import HttpRequest, HttpTransport

_USGS_DOMAINS = frozenset({"earthquake.usgs.gov"})


class WorldMonitorOfficialError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WorldMonitorOfficialClient:
    base_url: str
    transport: HttpTransport
    timeout_s: int

    def refresh_earthquakes(
        self, *, start_ms: int, end_ms: int, limit: int, now_ms: int
    ) -> tuple[IntelligenceRecord, ...]:
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError("invalid earthquake time range")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = urlencode({"start": start_ms, "end": end_ms, "page_size": limit})
        response = self.transport.send(
            HttpRequest(
                "GET",
                f"{self.base_url.rstrip('/')}/api/seismology/v1/list-earthquakes?{query}",
                timeout_s=float(self.timeout_s),
            )
        )
        if response.status != 200:
            raise WorldMonitorOfficialError(f"WorldMonitor HTTP {response.status}")
        try:
            body = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise WorldMonitorOfficialError("malformed WorldMonitor JSON") from exc
        raw_records = body.get("earthquakes") if isinstance(body, dict) else None
        if not isinstance(raw_records, list):
            raise WorldMonitorOfficialError("WorldMonitor response has no earthquakes array")
        records: list[IntelligenceRecord] = []
        for raw in raw_records:
            if not isinstance(raw, dict):
                raise WorldMonitorOfficialError("WorldMonitor earthquake was not an object")
            try:
                records.append(self._normalize_earthquake(raw, now_ms=now_ms))
            except (KeyError, TypeError, ValueError, WorldMonitorError) as exc:
                raise WorldMonitorOfficialError(str(exc)) from exc
        return tuple(records)

    @staticmethod
    def _normalize_earthquake(raw: Mapping[str, object], *, now_ms: int) -> IntelligenceRecord:
        location = raw.get("location")
        if not isinstance(location, dict):
            raise ValueError("location is malformed")
        magnitude = raw.get("magnitude")
        place = raw.get("place")
        if not isinstance(magnitude, (int, float)) or isinstance(magnitude, bool):
            raise ValueError("magnitude is malformed")
        if not isinstance(place, str):
            raise ValueError("place is malformed")
        canonical: dict[str, object] = {
            "id": raw.get("id", ""),
            "source_name": "USGS via WorldMonitor",
            "source_url": raw.get("sourceUrl", ""),
            "geography": f"{location.get('latitude')},{location.get('longitude')}",
            "summary": f"M{magnitude} — {place}",
            "observed_at": raw.get("occurredAt"),
        }
        return normalize_record(
            canonical,
            category=Category.DISASTERS,
            now=now_ms,
            ttl_s=15 * 60 * 1000,
            approved_source_domains=_USGS_DOMAINS,
        )


__all__ = ["WorldMonitorOfficialClient", "WorldMonitorOfficialError"]
