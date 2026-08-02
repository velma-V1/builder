"""WorldMonitor integration tests — brokered, capability-gated, provenance-safe, fail-closed."""

from __future__ import annotations

import pytest

from factory.integrations.worldmonitor import (
    WORLDMONITOR_MANIFEST,
    AiCapabilityRequest,
    AiResult,
    BrokeredWorldMonitorHttp,
    CapabilitySet,
    Category,
    Freshness,
    HealthState,
    UiMessage,
    WorldMonitorAdapter,
    WorldMonitorError,
    WorldMonitorMode,
    WorldMonitorNetworkPolicy,
    WorldMonitorQuery,
    discovered_tools,
    validate_ui_message,
)
from factory.integrations.worldmonitor.fake_transport import (
    fake_mcp,
    records_payload,
    rest_response,
    rest_transport_for,
    sample_record,
)
from factory.network.fake_backend import FakeNetworkBackend
from factory.network.models import NetworkApproval
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpRequest, HttpResponse
from factory.routing.models import Privacy
from factory.secret.fake_backend import FakeSecretBackend

pytestmark = pytest.mark.security

_HOST = "api.worldmonitor.example"
_BASE = f"https://{_HOST}"
_SOURCE_DOMAINS = frozenset({"feeds.worldmonitor.example"})
_UI_ORIGINS = frozenset({"https://workspace.builder.local"})


class FakeRouter:
    """A ModelRouterPort double — the ONLY AI path WorldMonitor may use."""

    def __init__(self) -> None:
        self.calls: list[AiCapabilityRequest] = []

    def request(self, capability: AiCapabilityRequest) -> AiResult:
        self.calls.append(capability)
        return AiResult(True, "routed summary", "fp-abc", "OLLAMA:qwen3:8b")


def _brokered(
    transport: FakeHttpTransport, *, max_bytes: int = 1_000_000
) -> BrokeredWorldMonitorHttp:
    approval = NetworkApproval(
        approval_id="A1",
        task_id="T1",
        destinations=frozenset({_HOST}),
        protocols=frozenset({"https"}),
        methods=frozenset({"GET"}),
        expires_at=10_000,
        max_total_bytes=max_bytes,
    )
    policy = WorldMonitorNetworkPolicy(task_id="T1", approval=approval, privacy=Privacy.LOCAL_ONLY)
    return BrokeredWorldMonitorHttp(
        transport, FakeNetworkBackend(), FakeSecretBackend({}), policy, 0
    )


def _adapter(
    transport: FakeHttpTransport,
    *,
    router: FakeRouter | None = None,
    categories: frozenset[Category] = frozenset({Category.WORLD_BRIEF}),
    now: int = 2000,
    brokered: BrokeredWorldMonitorHttp | None = None,
) -> WorldMonitorAdapter:
    return WorldMonitorAdapter(
        mode=WorldMonitorMode.LOCAL_REST,
        base_url=_BASE,
        brokered=brokered or _brokered(transport),
        capabilities=CapabilitySet(WorldMonitorMode.LOCAL_REST, categories),
        model_router=router or FakeRouter(),
        approved_source_domains=_SOURCE_DOMAINS,
        workspace_url="https://workspace.builder.local/wm",
        allowed_ui_origins=_UI_ORIGINS,
        clock=lambda: now,
    )


def test_health_states() -> None:
    for status, expected in [("healthy", HealthState.HEALTHY), ("degraded", HealthState.DEGRADED)]:
        transport = rest_transport_for("/health", rest_response({"status": status}))
        assert _adapter(transport).probe().state is expected
    err = rest_transport_for("/health", rest_response({"status": "x"}, status=503))
    assert _adapter(err).probe().state is HealthState.UNAVAILABLE


def test_capability_discovery_and_unsupported_denied() -> None:
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(sample_record()))
    )
    adapter = _adapter(transport, categories=frozenset({Category.WORLD_BRIEF}))
    assert adapter.discover_capabilities().supports(Category.WORLD_BRIEF)
    # A category not discovered is denied (fail closed).
    result = adapter.query(WorldMonitorQuery(Category.CYBER_THREATS))
    assert result.error_code == "CAPABILITY_UNAVAILABLE"


def test_rest_normalization_preserves_provenance_and_source() -> None:
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(sample_record()))
    )
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.ok and len(result.records) == 1
    rec = result.records[0]
    assert rec.source.source_url == "https://feeds.worldmonitor.example/item/1"
    assert rec.raw_reference  # raw reference preserved
    assert rec.provenance_chain[0].stage == "source"
    assert rec.confidence is None  # not supplied → never invented


def test_stale_data_is_marked() -> None:
    old = sample_record(observed_at=1)  # far in the past
    transport = rest_transport_for("/v1/world-brief", rest_response(records_payload(old)))
    # ttl default (normalized_ttl_s=86400); now huge → stale
    result = _adapter(transport, now=10_000_000).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.records[0].freshness.freshness is Freshness.STALE
    assert result.records[0].is_stale


def test_duplicate_detection() -> None:
    dup = sample_record()
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(dup, dict(dup)))
    )
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert len(result.records) == 1  # deduped by source identity + digest


def test_malformed_timestamp_rejected() -> None:
    bad = sample_record(observed_at="yesterday")
    transport = rest_transport_for("/v1/world-brief", rest_response(records_payload(bad)))
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "MALFORMED_RESPONSE"


def test_malformed_geography_rejected() -> None:
    bad = sample_record(geography=123)
    transport = rest_transport_for("/v1/world-brief", rest_response(records_payload(bad)))
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "MALFORMED_RESPONSE"


def test_malicious_source_url_rejected() -> None:
    bad = sample_record(source_url="https://evil.example/leak")
    transport = rest_transport_for("/v1/world-brief", rest_response(records_payload(bad)))
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "SOURCE_URL_DENIED"


def test_oversized_response_denied() -> None:
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(sample_record()))
    )
    brokered = _brokered(transport, max_bytes=1)  # 1-byte ceiling
    result = _adapter(transport, brokered=brokered).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "RESPONSE_TOO_LARGE"


def test_redirect_to_unapproved_host_denied() -> None:
    body = rest_response(records_payload(sample_record())).body

    def _m(req: HttpRequest) -> bool:
        return "/v1/world-brief" in req.url

    resp = HttpResponse(200, {"x-request-id": "r"}, body, final_url="https://evil.example/x")
    transport = FakeHttpTransport((FakeExchange(_m, resp),))
    result = _adapter(transport).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "NETWORK_DENIED"


def test_network_denied_when_host_not_approved() -> None:
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(sample_record()))
    )
    approval = NetworkApproval(
        approval_id="A1",
        task_id="T1",
        destinations=frozenset({"other.example"}),
        protocols=frozenset({"https"}),
        methods=frozenset({"GET"}),
        expires_at=10_000,
        max_total_bytes=1_000_000,
    )
    policy = WorldMonitorNetworkPolicy("T1", approval, privacy=Privacy.LOCAL_ONLY)
    brokered = BrokeredWorldMonitorHttp(
        transport, FakeNetworkBackend(), FakeSecretBackend({}), policy, 0
    )
    result = _adapter(transport, brokered=brokered).query(WorldMonitorQuery(Category.WORLD_BRIEF))
    assert result.error_code == "NETWORK_DENIED"
    assert transport.sent == []


def test_mcp_discovery_is_read_only() -> None:
    card_tools = discovered_tools(fake_mcp("intel.search", "intel.brief"))
    assert card_tools == ("intel.search", "intel.brief")


def test_ai_access_goes_only_through_builder_router() -> None:
    router = FakeRouter()
    transport = rest_transport_for(
        "/v1/world-brief", rest_response(records_payload(sample_record()))
    )
    adapter = _adapter(transport, router=router)
    result = adapter.request_ai("T1", "summarize", "brief this", privacy=Privacy.LOCAL_ONLY)
    assert result.ok and result.provider_route == "OLLAMA:qwen3:8b"
    assert len(router.calls) == 1  # WM never called a provider directly
    # WorldMonitorAdapter holds no provider adapter or secret handle — only a brokered http seam
    # and a model-router port. Its only AI slot is the router.
    slots = set(WorldMonitorAdapter.__slots__)
    assert "_router" in slots
    assert not any("provider" in s or "secret" in s for s in slots)


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        (UiMessage("focus_region", 1, "EU", "https://evil.example"), "origin"),
        (UiMessage("delete_everything", 1, "", "https://workspace.builder.local"), "unknown"),
        (UiMessage("open_country", 9, "US", "https://workspace.builder.local"), "version"),
        (UiMessage("open_panel", 1, "https://x.example", "https://workspace.builder.local"), "url"),
        (
            UiMessage("open_panel", 1, "authorization=abc", "https://workspace.builder.local"),
            "secret",
        ),
    ],
)
def test_ui_message_injection_rejected(message: UiMessage, reason: str) -> None:
    with pytest.raises(WorldMonitorError):
        validate_ui_message(message, allowed_origins=_UI_ORIGINS)


def test_ui_valid_command_accepted() -> None:
    cmd = validate_ui_message(
        UiMessage("focus_region", 1, "EU", "https://workspace.builder.local"),
        allowed_origins=_UI_ORIGINS,
    )
    assert cmd.command.value == "focus_region" and cmd.argument == "EU"


def test_license_and_attribution_manifest_present() -> None:
    assert "koala73/worldmonitor" in WORLDMONITOR_MANIFEST.upstream_repo
    assert WORLDMONITOR_MANIFEST.attribution
    assert "UNRESOLVED" in WORLDMONITOR_MANIFEST.commercial_use_status
    assert WORLDMONITOR_MANIFEST.license_verified is False
