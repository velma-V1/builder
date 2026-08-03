import json

import pytest

from factory.integrations.worldmonitor.manifest import WORLDMONITOR_MANIFEST
from factory.integrations.worldmonitor.official_client import (
    WorldMonitorOfficialClient,
    WorldMonitorOfficialError,
)
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpResponse


def _response(payload: dict[str, object], status: int = 200) -> HttpResponse:
    return HttpResponse(status, {}, json.dumps(payload).encode(), "http://127.0.0.1:3000")


def test_refresh_earthquakes_uses_pinned_sebuf_contract_and_preserves_usgs_provenance() -> None:
    transport = FakeHttpTransport(
        (
            FakeExchange(
                lambda request: "/api/seismology/v1/list-earthquakes?" in request.url,
                _response(
                    {
                        "earthquakes": [
                            {
                                "id": "us7000abcd",
                                "place": "10 km SW of Anchorage",
                                "magnitude": 5.2,
                                "depthKm": 12.5,
                                "location": {"latitude": 61.1, "longitude": -149.9},
                                "occurredAt": 1000,
                                "sourceUrl": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd",
                            }
                        ]
                    }
                ),
            ),
        )
    )
    client = WorldMonitorOfficialClient("http://127.0.0.1:3000", transport, timeout_s=20)

    records = client.refresh_earthquakes(start_ms=1, end_ms=2000, limit=25, now_ms=2500)

    assert len(records) == 1
    assert records[0].source.source_name == "USGS via WorldMonitor"
    assert records[0].source.upstream_record_id == "us7000abcd"
    assert records[0].normalized_summary == "M5.2 — 10 km SW of Anchorage"
    assert records[0].raw_reference.startswith("https://earthquake.usgs.gov/")
    assert records[0].provenance_chain
    assert "page_size=25" in transport.sent[0].url


def test_refresh_reports_degraded_source_without_fabricating_records() -> None:
    transport = FakeHttpTransport(
        (FakeExchange(lambda _request: True, HttpResponse(503, {}, b"unavailable")),)
    )
    client = WorldMonitorOfficialClient("http://127.0.0.1:3000", transport, timeout_s=20)

    with pytest.raises(WorldMonitorOfficialError, match="HTTP 503"):
        client.refresh_earthquakes(start_ms=1, end_ms=2, limit=10, now_ms=3)


def test_refresh_rejects_non_usgs_source_urls() -> None:
    transport = FakeHttpTransport(
        (
            FakeExchange(
                lambda _request: True,
                _response(
                    {
                        "earthquakes": [
                            {
                                "id": "bad",
                                "place": "bad",
                                "magnitude": 1,
                                "depthKm": 1,
                                "location": {"latitude": 0, "longitude": 0},
                                "occurredAt": 1,
                                "sourceUrl": "https://attacker.example/event",
                            }
                        ]
                    }
                ),
            ),
        )
    )
    client = WorldMonitorOfficialClient("http://127.0.0.1:3000", transport, timeout_s=20)

    with pytest.raises(WorldMonitorOfficialError, match="source host"):
        client.refresh_earthquakes(start_ms=1, end_ms=2, limit=10, now_ms=3)


def test_manifest_reports_full_approved_scope_and_earthquake_only_implementation() -> None:
    assert WORLDMONITOR_MANIFEST.approved_capability_scope == (
        "world_brief",
        "country_risk",
        "conflict_events",
        "military_activity",
        "cyber_threats",
        "disasters",
        "climate",
        "maritime",
        "aviation",
        "markets",
        "economic_indicators",
        "infrastructure",
        "news_research",
    )
    assert WORLDMONITOR_MANIFEST.implemented_capability_scope == ("disasters.earthquakes",)
    assert WORLDMONITOR_MANIFEST.section_complete is False
