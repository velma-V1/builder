"""Approved-model / approved-worker registry — CTR-ROUTE-REGISTRY (``03``, ``01J §2.1``).

The roster is the single source of approved *abstract routes*. It is immutable once activated
(``03 §6`` "no silent substitutions"; a change is an approval-gated new activation, never an
in-place edit). Two invariants are enforced structurally at activation:

* **Exclusion** — ``GLM-4.7`` / ``zai-glm-4.7`` may never appear in any route, default, or fallback
  list (``03 §6``); :func:`ApprovedRoster.activate` rejects them.
* **Local-first hierarchy** — :meth:`ApprovedRoster.candidates_for` returns the ``03 §7`` ordered
  candidate list for a task type, local routes first, hosted only as approved secondary capacity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from factory.routing.errors import RoutingError
from factory.routing.models import (
    ModelDescriptor,
    ModelRole,
    Provider,
    ResourceClass,
    TaskType,
)

# Case-folded identifiers that must never appear anywhere in the roster (``03 §6``).
EXCLUDED_MODEL_IDS = frozenset({"glm-4.7", "zai-glm-4.7"})

# Exact local model ids (``03 §3``).
QWEN_8B = "qwen3:8b"
QWEN_14B = "qwen3:14b"
AIDER_WORKER = "aider"


def _d(
    provider: Provider,
    model_id: str,
    role: ModelRole,
    resource_class: ResourceClass,
    is_local: bool,
) -> ModelDescriptor:
    return ModelDescriptor(provider, model_id, role, resource_class, is_local)


_LIGHT = ResourceClass.GPU_LIGHT
_HEAVY = ResourceClass.GPU_HEAVY
_CPU = ResourceClass.CPU_ONLY

_DEFAULT_DESCRIPTORS: tuple[ModelDescriptor, ...] = (
    _d(Provider.OLLAMA, QWEN_8B, ModelRole.DISPATCHER, _LIGHT, True),
    _d(Provider.OLLAMA, QWEN_14B, ModelRole.SUPERVISOR, _HEAVY, True),
    _d(Provider.AIDER, AIDER_WORKER, ModelRole.CODING_WORKER, _HEAVY, True),
    _d(Provider.GROQ, "qwen/qwen3.6-27b", ModelRole.HOSTED_WORKER, _CPU, False),
    _d(Provider.GROQ, "openai/gpt-oss-120b", ModelRole.HOSTED_REVIEWER, _CPU, False),
    _d(Provider.CEREBRAS, "qwen-3-235b-a22b-instruct-2507", ModelRole.HOSTED_WORKER, _CPU, False),
    _d(Provider.NVIDIA, "poolside/laguna-xs-2.1", ModelRole.HOSTED_WORKER, _CPU, False),
    _d(
        Provider.NVIDIA, "nvidia/nemotron-3-ultra-550b-a55b", ModelRole.HOSTED_REVIEWER, _CPU, False
    ),
)

# Deterministic ``03 §7`` local-first candidate order per task type. Each tuple lists route keys in
# strict priority order (local before hosted); the router honors this order verbatim.
_ROUTES: Mapping[TaskType, tuple[str, ...]] = {
    TaskType.DISPATCH: (f"OLLAMA:{QWEN_8B}",),
    TaskType.CLASSIFICATION: (f"OLLAMA:{QWEN_8B}",),
    TaskType.SUMMARY: (f"OLLAMA:{QWEN_8B}",),
    TaskType.CHAT: (f"OLLAMA:{QWEN_8B}",),
    TaskType.NAVIGATION: (f"OLLAMA:{QWEN_8B}",),
    TaskType.ROUTINE_CODING: (f"AIDER:{AIDER_WORKER}", f"OLLAMA:{QWEN_8B}"),
    TaskType.HARD_CODING: (
        f"AIDER:{AIDER_WORKER}",
        f"OLLAMA:{QWEN_14B}",
        "GROQ:qwen/qwen3.6-27b",
    ),
    TaskType.REPAIR: (f"OLLAMA:{QWEN_14B}", f"AIDER:{AIDER_WORKER}"),
    TaskType.PLANNING: (f"OLLAMA:{QWEN_14B}",),
    TaskType.ARCHITECTURE_REVIEW: (f"OLLAMA:{QWEN_14B}", "GROQ:openai/gpt-oss-120b"),
    TaskType.ESCALATION_REVIEW: (f"OLLAMA:{QWEN_14B}", "GROQ:openai/gpt-oss-120b"),
    TaskType.RECOVERY: (f"OLLAMA:{QWEN_14B}",),
}


class ApprovedRoster:
    """Immutable activated registry of approved abstract routes."""

    __slots__ = ("_by_key", "_routes")

    def __init__(
        self,
        descriptors: Sequence[ModelDescriptor],
        routes: Mapping[TaskType, tuple[str, ...]],
    ) -> None:
        self._by_key: dict[str, ModelDescriptor] = {d.route_key: d for d in descriptors}
        self._routes: dict[TaskType, tuple[str, ...]] = dict(routes)

    @classmethod
    def activate(
        cls,
        descriptors: Sequence[ModelDescriptor] = _DEFAULT_DESCRIPTORS,
        routes: Mapping[TaskType, tuple[str, ...]] = _ROUTES,
    ) -> ApprovedRoster:
        """Validate + activate a roster. Rejects excluded models and unknown route references."""
        for descriptor in descriptors:
            if descriptor.model_id.strip().lower() in EXCLUDED_MODEL_IDS:
                raise RoutingError(
                    "MODEL_EXCLUDED", f"excluded model may not be rostered: {descriptor.model_id}"
                )
        known = {d.route_key for d in descriptors}
        for task_type, ordered in routes.items():
            if not ordered:
                raise RoutingError("ROUTE_EMPTY", f"no candidate route for {task_type.value}")
            for route_key in ordered:
                if route_key not in known:
                    raise RoutingError(
                        "ROUTE_UNKNOWN", f"route {route_key} for {task_type.value} is not rostered"
                    )
        return cls(descriptors, routes)

    def is_approved(self, route_key: str) -> bool:
        return route_key in self._by_key

    def descriptor(self, route_key: str) -> ModelDescriptor:
        try:
            return self._by_key[route_key]
        except KeyError:
            raise RoutingError("ROUTE_UNKNOWN", f"route {route_key} is not approved") from None

    def candidates_for(self, task_type: TaskType) -> tuple[str, ...]:
        try:
            return self._routes[task_type]
        except KeyError:
            raise RoutingError(
                "ROUTE_UNDEFINED", f"no route defined for {task_type.value}"
            ) from None

    def local_route_keys(self) -> tuple[str, ...]:
        return tuple(k for k, d in self._by_key.items() if d.is_local)
