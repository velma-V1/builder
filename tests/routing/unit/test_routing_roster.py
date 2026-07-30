"""PH-4 unit — approved roster / CTR-ROUTE-REGISTRY (GLM exclusion, route validation)."""

from __future__ import annotations

import pytest

from factory.routing import ModelDescriptor, ModelRole, Provider, ResourceClass, TaskType
from factory.routing.errors import RoutingError
from factory.routing.roster import ApprovedRoster


def test_activate_default_roster_has_local_first_dispatch() -> None:
    roster = ApprovedRoster.activate()
    assert roster.candidates_for(TaskType.DISPATCH) == ("OLLAMA:qwen3:8b",)
    assert roster.is_approved("OLLAMA:qwen3:8b")
    assert not roster.is_approved("OLLAMA:nope")


def test_local_route_keys_are_local_only() -> None:
    roster = ApprovedRoster.activate()
    local = roster.local_route_keys()
    assert "OLLAMA:qwen3:8b" in local
    assert "AIDER:aider" in local
    assert "GROQ:qwen/qwen3.6-27b" not in local


@pytest.mark.security
@pytest.mark.parametrize("excluded", ["glm-4.7", "GLM-4.7", "zai-glm-4.7", " Zai-GLM-4.7 "])
def test_glm_models_are_rejected_from_the_roster(excluded: str) -> None:
    bad = ModelDescriptor(
        Provider.OLLAMA, excluded, ModelRole.DISPATCHER, ResourceClass.GPU_LIGHT, True
    )
    with pytest.raises(RoutingError) as exc:
        ApprovedRoster.activate(descriptors=(bad,), routes={})
    assert exc.value.code == "MODEL_EXCLUDED"


def test_activate_rejects_route_referencing_unknown_model() -> None:
    d = ModelDescriptor(
        Provider.OLLAMA, "qwen3:8b", ModelRole.DISPATCHER, ResourceClass.GPU_LIGHT, True
    )
    with pytest.raises(RoutingError) as exc:
        ApprovedRoster.activate(descriptors=(d,), routes={TaskType.DISPATCH: ("OLLAMA:ghost",)})
    assert exc.value.code == "ROUTE_UNKNOWN"


def test_activate_rejects_empty_route_list() -> None:
    d = ModelDescriptor(
        Provider.OLLAMA, "qwen3:8b", ModelRole.DISPATCHER, ResourceClass.GPU_LIGHT, True
    )
    with pytest.raises(RoutingError) as exc:
        ApprovedRoster.activate(descriptors=(d,), routes={TaskType.DISPATCH: ()})
    assert exc.value.code == "ROUTE_EMPTY"


def test_descriptor_lookup_unknown_raises() -> None:
    roster = ApprovedRoster.activate()
    with pytest.raises(RoutingError) as exc:
        roster.descriptor("OLLAMA:ghost")
    assert exc.value.code == "ROUTE_UNKNOWN"


def test_candidates_for_undefined_task_type_raises() -> None:
    d = ModelDescriptor(
        Provider.OLLAMA, "qwen3:8b", ModelRole.DISPATCHER, ResourceClass.GPU_LIGHT, True
    )
    roster = ApprovedRoster.activate(
        descriptors=(d,), routes={TaskType.DISPATCH: ("OLLAMA:qwen3:8b",)}
    )
    with pytest.raises(RoutingError) as exc:
        roster.candidates_for(TaskType.RECOVERY)
    assert exc.value.code == "ROUTE_UNDEFINED"
