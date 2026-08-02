"""RPH3-T5 unit — Tool Registry: default-deny, complete declaration/provenance, quarantine."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from factory.tools import (
    OutputSchema,
    Provenance,
    RegistrationRequest,
    ToolDeclaration,
    ToolError,
    ToolRegistry,
    ToolState,
)

DeclFactory = Callable[..., ToolDeclaration]
RegisterTool = Callable[..., ToolDeclaration]


def _request(declaration: ToolDeclaration, *, downloaded: bool = True) -> RegistrationRequest:
    return RegistrationRequest(
        declaration=declaration,
        provenance=Provenance(source="github", checksum="sha:abc", license="MIT"),
        output_schema=OutputSchema(kind="json", max_bytes=4096, required_keys=("ok",)),
        downloaded=downloaded,
    )


def test_register_and_lookup(registry: ToolRegistry, make_declaration: DeclFactory) -> None:
    verdict = registry.register(_request(make_declaration()))
    assert verdict.approved
    assert registry.lookup("formatter", "1.0") is not None
    assert registry.is_registered("formatter", "1.0")


def test_unregistered_is_default_deny(registry: ToolRegistry) -> None:
    assert registry.lookup("ghost", "9") is None
    assert registry.is_registered("ghost", "9") is False


def test_incomplete_declaration_rejected(registry: ToolRegistry) -> None:
    bad = ToolDeclaration(
        tool_id="x",
        version="1",
        capabilities=(),
        inputs=(),
        outputs=(),
        side_effects=(),
        permission_classes=(),
        environment="",
        resource_profile="",
        failure_behavior="",
    )
    verdict = registry.register(_request(bad))
    assert not verdict.approved
    assert "declaration" in verdict.reason


def test_incomplete_provenance_rejected_for_download(
    registry: ToolRegistry, make_declaration: DeclFactory
) -> None:
    request = RegistrationRequest(
        declaration=make_declaration(),
        provenance=Provenance(source="", checksum="", license=""),
        output_schema=OutputSchema(kind="json", max_bytes=10, required_keys=()),
        downloaded=True,
    )
    verdict = registry.register(request)
    assert not verdict.approved
    assert "provenance" in verdict.reason


def test_duplicate_registration_rejected(
    registry: ToolRegistry, make_declaration: DeclFactory
) -> None:
    assert registry.register(_request(make_declaration())).approved
    second = registry.register(_request(make_declaration()))
    assert not second.approved
    assert "already registered" in second.reason


def test_version_pinning_distinct_versions(
    registry: ToolRegistry, make_declaration: DeclFactory
) -> None:
    registry.register(_request(make_declaration(version="1.0")))
    registry.register(_request(make_declaration(version="2.0")))
    assert registry.lookup("formatter", "1.0") is not None
    assert registry.lookup("formatter", "2.0") is not None
    assert registry.lookup("formatter", "3.0") is None  # unpinned version uncallable


def test_quarantine_makes_uncallable_and_release_restores(
    registry: ToolRegistry, register_tool: RegisterTool
) -> None:
    register_tool()
    registry.quarantine("formatter", "1.0", "compromised")
    assert registry.lookup("formatter", "1.0") is None  # quarantined ⇒ uncallable
    record = registry.reader.get_record("formatter", "1.0")
    assert record is not None and record.state is ToolState.QUARANTINED
    registry.release("formatter", "1.0", "review-42")
    assert registry.lookup("formatter", "1.0") is not None  # released ⇒ callable again


def test_quarantine_guards(registry: ToolRegistry, register_tool: RegisterTool) -> None:
    with pytest.raises(ToolError) as exc:
        registry.quarantine("ghost", "1", "x")
    assert exc.value.code == "TOOL_NOT_FOUND"
    register_tool()
    registry.quarantine("formatter", "1.0", "x")
    with pytest.raises(ToolError) as exc2:
        registry.quarantine("formatter", "1.0", "again")
    assert exc2.value.code == "TOOL_ALREADY_QUARANTINED"


def test_release_guards(registry: ToolRegistry, register_tool: RegisterTool) -> None:
    register_tool()
    with pytest.raises(ToolError) as exc:
        registry.release("formatter", "1.0", "r")  # not quarantined
    assert exc.value.code == "TOOL_NOT_QUARANTINED"
    registry.quarantine("formatter", "1.0", "x")
    with pytest.raises(ToolError) as exc2:
        registry.release("formatter", "1.0", "")  # no review ref
    assert exc2.value.code == "TOOL_RELEASE_NEEDS_REVIEW"


def test_repeated_failure_quarantines(registry: ToolRegistry, register_tool: RegisterTool) -> None:
    register_tool()
    assert registry.record_failure("formatter", "1.0") is False  # 1
    assert registry.record_failure("formatter", "1.0") is False  # 2
    assert registry.record_failure("formatter", "1.0") is True  # 3 → quarantined
    assert registry.lookup("formatter", "1.0") is None


def test_record_failure_unknown_tool_raises(registry: ToolRegistry) -> None:
    with pytest.raises(ToolError) as exc:
        registry.record_failure("ghost", "1")
    assert exc.value.code == "TOOL_NOT_FOUND"
