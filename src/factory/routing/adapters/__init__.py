"""Routing-owned provider-adapter interface (Task 4.3).

Defines the uniform ``ProviderAdapter`` surface plus its call vocabulary. Concrete adapters live at
their plan-assigned owner paths (``factory.models.ollama_adapter`` and
``factory.workers.aider_adapter``) and implement this interface.
"""

from __future__ import annotations

from factory.routing.adapters.base import (
    CallRequest,
    CallResult,
    ProviderAdapter,
)

__all__ = [
    "CallRequest",
    "CallResult",
    "ProviderAdapter",
]
