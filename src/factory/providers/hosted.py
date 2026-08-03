"""Hosted-adapter base: task-scoped grants + ProviderAdapter conformance (fail-closed).

A hosted call needs a task-scoped grant (privacy + network approval + secret ref) that the plain
:class:`~factory.routing.adapters.base.ProviderAdapter` surface does not carry. The base resolves
that grant per task via an injected :class:`GrantResolver`, runs the request through the brokered
envelope, and returns a rich :class:`HostedResult` (carrying a provider-neutral
:class:`ProviderFingerprint`). It also implements ``probe/supports/call/cancel`` — a structural
drop-in for the existing adapter contract. An adapter never falls back to another model/provider,
never approves a discovered model, and never raises out of ``execute``/``call``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from factory.network.broker import NetworkBroker
from factory.network.models import NetworkApproval
from factory.providers.brokered import BrokeredContext, BrokeredHttp
from factory.providers.errors import ProviderError, ProviderErrorCode, status_for
from factory.providers.models import (
    ProviderConfiguration,
    ProviderFingerprint,
    ProviderResponseMetadata,
)
from factory.providers.openai_core import (
    ChatMessage,
    ChatRequest,
    CoreChatResult,
    OpenAICompatibleAdapterCore,
)
from factory.providers.transport import HttpTransport
from factory.routing.adapters.base import CallRequest, CallResult
from factory.routing.models import (
    CapabilityReport,
    ExecutionStatus,
    Privacy,
    RuntimeStatus,
)
from factory.secret.broker import SecretBroker
from factory.secret.models import SecretRef


@dataclass(frozen=True, slots=True)
class HostedGrant:
    """A task-scoped authorization to make a hosted call (carries route-level policy)."""

    privacy: Privacy
    approval: NetworkApproval
    secret_ref: SecretRef
    expected_upstream: str = ""
    endpoint_identity: str = ""
    region: str = ""
    #: Strict routes must name the exact upstream provider (refuse hidden auto-selection).
    strict_upstream: bool = True
    #: The route requires zero-data-retention / data-collection-deny where the provider supports it.
    require_zdr: bool = False


@runtime_checkable
class GrantResolver(Protocol):
    """Yields the task-scoped grant for a hosted call, or ``None`` when hosted use is denied."""

    def resolve(self, task_id: str) -> HostedGrant | None: ...


@dataclass(frozen=True, slots=True)
class HostedResult:
    status: ExecutionStatus
    output: str = ""
    tool_calls: tuple[str, ...] = ()
    tokens: int = 0
    metadata: ProviderResponseMetadata = field(default_factory=ProviderResponseMetadata)
    fingerprint: ProviderFingerprint | None = None
    error_code: str | None = None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ExecutionStatus.SUCCEEDED


class HostedAdapter:
    """Base for OpenAI-compatible hosted adapters (OpenRouter / Hugging Face / Together)."""

    __slots__ = (
        "_adapter_version",
        "_approved",
        "_auth_scheme",
        "_clock",
        "_config",
        "_core",
        "_network",
        "_resolver",
        "_routing_policy_version",
        "_secret",
        "_transport",
    )

    def __init__(
        self,
        config: ProviderConfiguration,
        core: OpenAICompatibleAdapterCore,
        transport: HttpTransport,
        network: NetworkBroker,
        secret: SecretBroker,
        resolver: GrantResolver,
        approved_models: frozenset[str],
        *,
        clock: Callable[[], int],
        adapter_version: str = "v1",
        routing_policy_version: str = "v1",
        auth_scheme: str = "Bearer",
    ) -> None:
        self._config = config
        self._core = core
        self._transport = transport
        self._network = network
        self._secret = secret
        self._resolver = resolver
        self._approved = approved_models
        self._clock = clock
        self._adapter_version = adapter_version
        self._routing_policy_version = routing_policy_version
        self._auth_scheme = auth_scheme

    # -- ProviderAdapter surface -----------------------------------------------------------
    @property
    def provider_name(self) -> str:
        return self._config.provider.value

    def supports(self, model_id: str) -> bool:
        """Exact-approved only. A discovered-but-unapproved model is NOT supported (fail closed)."""
        return model_id in self._approved

    def probe(self) -> CapabilityReport:
        # Honest: a hosted probe requires a task-scoped CLOUD_ALLOWED grant, so availability is not
        # asserted here (no live call). The exact approved model set is reported.
        return CapabilityReport(
            self._config.provider,
            RuntimeStatus.UNAVAILABLE,
            tuple(sorted(self._approved)),
            self._config.api_version,
            "hosted probe deferred: requires a task-scoped CLOUD_ALLOWED grant",
        )

    def call(self, request: CallRequest) -> CallResult:
        result = self.execute(request)
        # The legacy CallResult.fingerprint stays ModelFingerprint|None; hosted provenance travels
        # on HostedResult.fingerprint (schema 2). We surface its digest in the reason.
        digest = result.fingerprint.digest() if result.fingerprint is not None else ""
        reason = f"{result.reason} fp={digest}" if digest else result.reason
        return CallResult(
            status=result.status,
            output=result.output,
            tokens=result.tokens,
            fingerprint=None,
            reason=reason,
            error_code=result.error_code,
            tool_calls=result.tool_calls,
        )

    def cancel(self, task_id: str) -> bool:
        # Defensive: drop any secret leases for the task. Non-streaming fake has nothing in-flight.
        self._secret.revoke_task(task_id)
        return False

    # -- rich hosted execution -------------------------------------------------------------
    def execute(self, request: CallRequest) -> HostedResult:
        model_id = self._model_of(request.route_key)
        if not self.supports(model_id):
            return HostedResult(
                ExecutionStatus.FAILED,
                error_code=ProviderErrorCode.MODEL_MISSING.value,
                reason=f"model {model_id!r} is not in the approved roster (discovery != approval)",
            )
        grant = self._resolver.resolve(request.task_id)
        if grant is None:
            return HostedResult(
                ExecutionStatus.RUNTIME_UNAVAILABLE,
                error_code=ProviderErrorCode.NETWORK_DENIED.value,
                reason="no task-scoped CLOUD_ALLOWED grant; hosted call refused",
            )
        context = BrokeredContext(
            task_id=request.task_id,
            privacy=grant.privacy,
            network=self._network,
            approval=grant.approval,
            secret=self._secret,
            secret_ref=grant.secret_ref,
            now=self._clock(),
            auth_scheme=self._auth_scheme,
        )
        brokered = BrokeredHttp(self._transport, context)
        try:
            chat = self._shape(model_id, request, grant)
            core_result = self._core.chat(self._config, brokered, chat)
            if not core_result.ok:
                code = core_result.error_code or ProviderErrorCode.RUNTIME_UNAVAILABLE
                return HostedResult(
                    status_for(code),
                    metadata=core_result.metadata,
                    error_code=code.value,
                    reason=brokered.redact(core_result.reason),
                )
            fingerprint = self._fingerprint(model_id, grant, core_result)
            return HostedResult(
                ExecutionStatus.SUCCEEDED,
                output=core_result.output,
                tool_calls=core_result.tool_calls,
                tokens=core_result.metadata.usage.total_tokens,
                metadata=core_result.metadata,
                fingerprint=fingerprint,
                reason="ok",
            )
        except ProviderError as exc:
            return HostedResult(
                status_for(exc.code),
                error_code=exc.code.value,
                reason=brokered.redact(exc.detail),
            )

    # -- hooks -----------------------------------------------------------------------------
    def _model_of(self, route_key: str) -> str:
        return route_key.split(":", 1)[1] if ":" in route_key else route_key

    def _shape(self, model_id: str, request: CallRequest, grant: HostedGrant) -> ChatRequest:
        """Default: a plain chat request. Subclasses add provider-specific policy fields."""
        return ChatRequest(
            model=model_id,
            messages=(ChatMessage("user", request.prompt),),
            max_tokens=request.max_tokens,
            expected_upstream=grant.expected_upstream,
        )

    def _fingerprint(
        self, model_id: str, grant: HostedGrant, core_result: CoreChatResult
    ) -> ProviderFingerprint:
        metadata = core_result.metadata
        return ProviderFingerprint(
            provider=self._config.provider,
            model_id=model_id,
            model_version_or_digest=metadata.returned_model or model_id,
            upstream_provider=metadata.upstream_provider or grant.expected_upstream,
            endpoint_identity=grant.endpoint_identity,
            runtime_or_api_version=self._config.api_version,
            context_window=0,
            capability_digest="",
            sampling=(),
            system_prompt_version="v1",
            tool_schema_version="v1",
            adapter_version=self._adapter_version,
            routing_policy_version=self._routing_policy_version,
            execution_region=grant.region,
        )

    def discover(self, task_id: str) -> tuple[str, ...]:
        """Read-only discovery of model ids (catalog only; NEVER approval)."""
        grant = self._resolver.resolve(task_id)
        if grant is None:
            return ()
        context = BrokeredContext(
            task_id=task_id,
            privacy=grant.privacy,
            network=self._network,
            approval=grant.approval,
            secret=self._secret,
            secret_ref=grant.secret_ref,
            now=self._clock(),
            auth_scheme=self._auth_scheme,
        )
        brokered = BrokeredHttp(self._transport, context)
        try:
            return tuple(m.model_id for m in self._core.discover_models(self._config, brokered))
        except ProviderError:
            return ()
