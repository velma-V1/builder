"""Runtime capability discovery — unknown capability is DENIED (fail closed).

Never assume a mode exposes a capability: a local image may not expose the hosted REST API or MCP,
and not every category exists in every mode. Capabilities must be *discovered*; anything not
discovered is denied.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.integrations.worldmonitor.errors import WorldMonitorError, WorldMonitorErrorCode
from factory.integrations.worldmonitor.models import Category, WorldMonitorMode


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    mode: WorldMonitorMode
    categories: frozenset[Category]

    def supports(self, category: Category) -> bool:
        return category in self.categories


def require_capability(capabilities: CapabilitySet, category: Category) -> None:
    """Raise ``CAPABILITY_UNAVAILABLE`` unless ``category`` was discovered for this mode."""
    if not capabilities.supports(category):
        raise WorldMonitorError(
            WorldMonitorErrorCode.CAPABILITY_UNAVAILABLE,
            f"capability {category.value!r} not discovered in mode {capabilities.mode.value}",
        )
