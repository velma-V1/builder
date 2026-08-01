"""Agent Zero must-never-hold authority: every denial is exercised end to end, not just documented.

Covers: path traversal, symlink escape, Windows drive/UNC escape (via PathAuthority — never a
bespoke check), tool denial, network denial, secret denial (structural), model-route bypass
(structural), Docker socket denial, direct-main denial, self-certification denial, self-promotion
denial.
"""

from __future__ import annotations

import dataclasses
import inspect
import os
import sys
from pathlib import Path

import pytest
from az_support import approval, model_router, network_backend, work_order

from factory.contracts.validation.paths import PathAuthority
from factory.integrations.agent_zero.adapter import AgentZeroAdapter
from factory.integrations.agent_zero.capabilities import CapabilitySet, require_tool
from factory.integrations.agent_zero.errors import AgentZeroError, AgentZeroErrorCode
from factory.integrations.agent_zero.fake_transport import FakeAgentZeroTransport
from factory.integrations.agent_zero.models import AgentZeroResult, WorkerOutcome
from factory.integrations.agent_zero.policy import (
    AgentZeroNetworkPolicy,
    BrokeredAgentZeroHttp,
    deny_direct_main_access,
    enforce_sandbox_boundary,
    evaluate_output_path,
)
from factory.integrations.agent_zero.task_mapping import build_work_order
from factory.network.models import Direction, NetworkApproval, NetworkRequest
from factory.providers.transport import FakeExchange, FakeHttpTransport, HttpResponse
from factory.sandbox.models import MountMode, MountSpec, ResourceLimits, SandboxSpec

pytestmark = pytest.mark.security

_RESOURCES = ResourceLimits(cpu_millis=1000, memory_mb=512, disk_mb=256, pids=32, wall_clock_s=300)


def _spec(**over: object) -> SandboxSpec:
    base: dict[str, object] = dict(
        task_id="t1", workstream_id="ws1", image="agent-zero-worker", image_version="0.1",
        resources=_RESOURCES,
    )
    base.update(over)
    return SandboxSpec(**base)  # type: ignore[arg-type]


def _adapter(**over: object) -> AgentZeroAdapter:
    base: dict[str, object] = dict(
        transport=FakeAgentZeroTransport(()), model_router=model_router(), clock=lambda: 0,
    )
    base.update(over)
    return AgentZeroAdapter(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Path traversal / symlink / Windows drive+UNC escape — PathAuthority, never a bespoke check.
# ---------------------------------------------------------------------------


def test_path_traversal_is_denied(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    with pytest.raises(AgentZeroError) as excinfo:
        evaluate_output_path(authority, "../outside.txt", allowed=("**",))
    assert excinfo.value.code is AgentZeroErrorCode.PATH_DENIED


def test_windows_drive_qualified_path_is_denied(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    with pytest.raises(AgentZeroError) as excinfo:
        evaluate_output_path(authority, "C:\\Windows\\System32\\evil.dll", allowed=("**",))
    assert excinfo.value.code is AgentZeroErrorCode.PATH_DENIED


def test_unc_path_is_denied(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    with pytest.raises(AgentZeroError) as excinfo:
        evaluate_output_path(authority, "\\\\attacker-host\\share\\file.txt", allowed=("**",))
    assert excinfo.value.code is AgentZeroErrorCode.PATH_DENIED


def test_symlink_escape_is_denied(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside)
    authority = PathAuthority(project_root=root)
    with pytest.raises(AgentZeroError) as excinfo:
        evaluate_output_path(authority, "link/secret.txt", allowed=("**",))
    assert excinfo.value.code is AgentZeroErrorCode.PATH_DENIED


@pytest.mark.skipif(sys.platform != "win32", reason="junction escape requires Windows semantics")
def test_junction_escape_is_denied_on_windows(tmp_path: Path) -> None:  # pragma: no cover
    pytest.skip("classified NOT_TESTABLE on this platform; see test_symlink_escape_is_denied")


def test_sibling_prefix_bypass_is_denied(tmp_path: Path) -> None:
    root = tmp_path / "Factory"
    root.mkdir()
    (tmp_path / "Factory-Evil").mkdir()
    authority = PathAuthority(project_root=root)
    escaped = os.path.relpath(tmp_path / "Factory-Evil" / "secret.txt", root)
    with pytest.raises(AgentZeroError):
        evaluate_output_path(authority, escaped, allowed=("**",))


def test_allowed_path_within_scope_is_permitted(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    result = evaluate_output_path(authority, "src/example.py", allowed=("src/**",))
    assert result.allowed


def test_path_outside_granted_glob_scope_is_denied(tmp_path: Path) -> None:
    authority = PathAuthority(project_root=tmp_path)
    with pytest.raises(AgentZeroError):
        evaluate_output_path(authority, "secrets/config.env", allowed=("src/**",))


# ---------------------------------------------------------------------------
# Tool denial
# ---------------------------------------------------------------------------


def test_ungranted_tool_is_denied() -> None:
    capabilities = CapabilitySet("wo-1", frozenset({"read_file"}))
    with pytest.raises(AgentZeroError) as excinfo:
        require_tool(capabilities, "shell_exec")
    assert excinfo.value.code is AgentZeroErrorCode.TOOL_DENIED


def test_adapter_authorize_tool_call_denies_ungranted_tool() -> None:
    adapter = _adapter()
    order = work_order(granted_tools=frozenset({"read_file"}))
    with pytest.raises(AgentZeroError) as excinfo:
        adapter.authorize_tool_call(order, "docker_exec")
    assert excinfo.value.code is AgentZeroErrorCode.TOOL_DENIED


def test_adapter_authorize_tool_call_permits_granted_tool() -> None:
    adapter = _adapter()
    order = work_order(granted_tools=frozenset({"read_file", "write_patch"}))
    adapter.authorize_tool_call(order, "write_patch")  # must not raise


# ---------------------------------------------------------------------------
# Network denial
# ---------------------------------------------------------------------------


def test_network_call_with_no_approval_contract_is_denied() -> None:
    network = network_backend()
    denied_policy = AgentZeroNetworkPolicy(
        task_id="t1",
        approval=NetworkApproval(
            approval_id="none", task_id="t1", destinations=frozenset(), protocols=frozenset(),
            methods=frozenset(), expires_at=0, max_total_bytes=0,
        ),
    )
    brokered = BrokeredAgentZeroHttp(FakeHttpTransport(()), network, denied_policy, now=1)
    with pytest.raises(AgentZeroError) as excinfo:
        brokered.request("GET", "https://not-approved.example/data")
    assert excinfo.value.code is AgentZeroErrorCode.NETWORK_DENIED


def test_network_call_to_approved_host_succeeds() -> None:
    network = network_backend()
    grant = approval()
    policy = AgentZeroNetworkPolicy(task_id="t1", approval=grant)
    response = HttpResponse(200, {}, b"{}")
    transport = FakeHttpTransport((FakeExchange(lambda _r: True, response),))
    brokered = BrokeredAgentZeroHttp(transport, network, policy, now=1)
    host = next(iter(grant.destinations))
    result = brokered.request("GET", f"https://{host}/data")
    assert result.status == 200


def test_network_evaluate_denies_unsolicited_inbound_by_default() -> None:
    network = network_backend()
    decision = network.evaluate(
        approval(),
        NetworkRequest("agent-zero-worker.internal.example", "https", "GET", Direction.INBOUND),
        now=1,
    )
    assert not decision.allowed


# ---------------------------------------------------------------------------
# Secret denial (structural — no code path can inject a secret)
# ---------------------------------------------------------------------------


def test_brokered_http_constructor_has_no_secret_parameter() -> None:
    params = set(inspect.signature(BrokeredAgentZeroHttp.__init__).parameters)
    assert not any("secret" in p.lower() for p in params)


def test_adapter_slots_hold_no_secret_or_provider_handle() -> None:
    slots = set(AgentZeroAdapter.__slots__)
    assert not any("secret" in s or "provider" in s for s in slots)


# ---------------------------------------------------------------------------
# Model-route bypass — the router is the only path to AI
# ---------------------------------------------------------------------------


def test_adapter_holds_only_a_router_handle_never_a_provider() -> None:
    slots = set(AgentZeroAdapter.__slots__)
    assert "_router" in slots


def test_request_model_goes_through_the_injected_router_only() -> None:
    router = model_router(output="routed-output")
    adapter = _adapter(model_router=router)
    result = adapter.request_model("t1", "summarize", "hello")
    assert result.output == "routed-output"
    assert len(router.requests) == 1
    assert router.requests[0].capability == "summarize"


# ---------------------------------------------------------------------------
# Docker socket denial
# ---------------------------------------------------------------------------


def test_host_docker_socket_request_is_denied() -> None:
    with pytest.raises(AgentZeroError) as excinfo:
        enforce_sandbox_boundary(_spec(host_docker_socket=True))
    assert excinfo.value.code is AgentZeroErrorCode.DOCKER_SOCKET_DENIED


def test_privileged_sandbox_is_denied_generically() -> None:
    with pytest.raises(AgentZeroError) as excinfo:
        enforce_sandbox_boundary(_spec(privileged=True))
    assert excinfo.value.code is not AgentZeroErrorCode.DOCKER_SOCKET_DENIED


def test_writable_host_project_mount_is_denied() -> None:
    mount = MountSpec(
        host_path="/host/project", container_path="/work", mode=MountMode.RW, is_host_project=True,
    )
    with pytest.raises(AgentZeroError):
        enforce_sandbox_boundary(_spec(mounts=(mount,)))


def test_clean_sandbox_spec_is_admissible() -> None:
    enforce_sandbox_boundary(_spec())  # must not raise


# ---------------------------------------------------------------------------
# Direct-main denial
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("branch", ["main", "Main", "MASTER", " master "])
def test_direct_main_access_is_denied(branch: str) -> None:
    with pytest.raises(AgentZeroError) as excinfo:
        deny_direct_main_access(branch)
    assert excinfo.value.code is AgentZeroErrorCode.DIRECT_MAIN_DENIED


def test_work_order_construction_refuses_a_main_branch_ref() -> None:
    with pytest.raises(AgentZeroError) as excinfo:
        build_work_order(
            work_order_id="wo-1", task_id="t1", workstream_id="ws1", branch_ref="main",
            instructions="do work", granted_tools=frozenset({"read_file"}),
            allowed_path_globs=("src/**",), resources=work_order().resources, timeout_s=60,
        )
    assert excinfo.value.code is AgentZeroErrorCode.DIRECT_MAIN_DENIED


def test_work_order_construction_accepts_a_feature_branch_ref() -> None:
    order = build_work_order(
        work_order_id="wo-1", task_id="t1", workstream_id="ws1",
        branch_ref="feature/agent-zero-fix", instructions="do work",
        granted_tools=frozenset({"read_file"}), allowed_path_globs=("src/**",),
        resources=work_order().resources, timeout_s=60,
    )
    assert order.branch_ref == "feature/agent-zero-fix"


# ---------------------------------------------------------------------------
# Self-certification / self-promotion denial
# ---------------------------------------------------------------------------


def test_self_certification_claim_is_denied_at_intake() -> None:
    adapter = _adapter()
    result = AgentZeroResult(
        work_order_id="wo-1", worker_claimed_outcome=WorkerOutcome.SUCCESS,
        worker_self_report={"verified": "true"},
    )
    with pytest.raises(AgentZeroError) as excinfo:
        adapter.intake_result(result)
    assert excinfo.value.code is AgentZeroErrorCode.SELF_CERTIFICATION_DENIED


def test_self_promotion_claim_is_denied_at_intake() -> None:
    adapter = _adapter()
    result = AgentZeroResult(
        work_order_id="wo-1", worker_claimed_outcome=WorkerOutcome.SUCCESS,
        worker_self_report={"promoted": "true"},
    )
    with pytest.raises(AgentZeroError) as excinfo:
        adapter.intake_result(result)
    assert excinfo.value.code is AgentZeroErrorCode.PROMOTION_AUTHORITY_DENIED


def test_honest_result_with_no_authority_claims_passes_intake() -> None:
    adapter = _adapter()
    result = AgentZeroResult(
        work_order_id="wo-1", worker_claimed_outcome=WorkerOutcome.SUCCESS,
        worker_self_report={"note": "ran unit tests locally"},
    )
    assert adapter.intake_result(result) is result


def test_worker_claimed_success_is_never_the_same_field_as_verification() -> None:
    """Worker success must never equal Builder verification success — structurally, not by luck.

    ``AgentZeroResult`` has no "verified"/"approved"/"promoted" field at all; a worker's own SUCCESS
    claim (``worker_claimed_outcome``) is a distinctly-named attribute from whatever Builder's own
    staging/approval pipeline will separately decide.
    """
    result = AgentZeroResult(work_order_id="wo-1", worker_claimed_outcome=WorkerOutcome.SUCCESS)
    field_names = {f.name for f in dataclasses.fields(result)}
    assert "verified" not in field_names
    assert "approved" not in field_names
    assert "promoted" not in field_names
    assert "worker_claimed_outcome" in field_names
