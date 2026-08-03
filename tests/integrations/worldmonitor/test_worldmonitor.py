"""WorldMonitor package-level security and immutable contract checks."""

from __future__ import annotations

import pytest

from factory.integrations.worldmonitor import (
    WORLDMONITOR_MANIFEST,
    CapabilitySet,
    Category,
    UiMessage,
    WorldMonitorError,
    WorldMonitorMode,
    discovered_tools,
    validate_ui_message,
)
from factory.integrations.worldmonitor.fake_transport import fake_mcp

pytestmark = pytest.mark.security

_UI_ORIGINS = frozenset({"https://workspace.builder.local"})


def test_capability_discovery_is_fail_closed() -> None:
    capabilities = CapabilitySet(WorldMonitorMode.LOCAL_REST, frozenset({Category.DISASTERS}))
    assert capabilities.supports(Category.DISASTERS)
    assert not capabilities.supports(Category.CYBER_THREATS)


def test_mcp_discovery_is_read_only() -> None:
    assert discovered_tools(fake_mcp("intel.search", "intel.brief")) == (
        "intel.search",
        "intel.brief",
    )


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
    with pytest.raises(WorldMonitorError) as raised:
        validate_ui_message(message, allowed_origins=_UI_ORIGINS)
    assert reason in str(raised.value).lower()


def test_ui_valid_command_accepted() -> None:
    command = validate_ui_message(
        UiMessage("focus_region", 1, "EU", "https://workspace.builder.local"),
        allowed_origins=_UI_ORIGINS,
    )
    assert command.command.value == "focus_region"
    assert command.argument == "EU"


def test_license_and_attribution_manifest_present() -> None:
    assert "koala73/worldmonitor" in WORLDMONITOR_MANIFEST.upstream_repo
    assert WORLDMONITOR_MANIFEST.attribution
    assert WORLDMONITOR_MANIFEST.license_verified is True
