"""Replicate adapter — prediction lifecycle (NOT chat-completion).

Replicate runs asynchronous predictions: create → (starting → processing) → succeeded / failed /
canceled. This adapter resolves an exact ``owner/name`` at a **pinned version**, validates input
against the approved schema keys, creates a prediction, waits with a bounded poll, normalizes the
output, and validates every output URL's host against the approved domains. Version drift, unknown
input keys, and unexpected output URLs all fail closed. Scope: prediction polling only — no
webhooks, deployments, model/version creation, training, or mutation APIs.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from factory.network.broker import NetworkBroker
from factory.providers.brokered import BrokeredContext, BrokeredHttp
from factory.providers.errors import ProviderError, ProviderErrorCode, map_http_status
from factory.providers.hosted import GrantResolver
from factory.providers.models import ProviderConfiguration
from factory.providers.transport import HttpResponse, HttpTransport
from factory.routing.adapters.base import CallRequest
from factory.secret.broker import SecretBroker


class PredictionState(StrEnum):
    STARTING = "starting"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


_TERMINAL = frozenset({PredictionState.SUCCEEDED, PredictionState.FAILED, PredictionState.CANCELED})


@dataclass(frozen=True, slots=True)
class ApprovedReplicateRoute:
    owner: str
    name: str
    version_id: str  # PINNED — an unpinned/mutable community route is rejected
    input_schema_keys: frozenset[str]
    approved_output_domains: frozenset[str]

    @property
    def model_id(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True, slots=True)
class ReplicatePrediction:
    prediction_id: str
    version_id: str
    state: PredictionState
    outputs: tuple[str, ...] = ()
    error_code: str | None = None
    reason: str = ""
    started_at: int = 0
    finished_at: int = 0

    @property
    def ok(self) -> bool:
        return self.state is PredictionState.SUCCEEDED


def _noop_sleep(_seconds: float) -> None:
    return None


class ReplicateAdapter:
    __slots__ = (
        "_clock",
        "_config",
        "_max_polls",
        "_network",
        "_poll_interval_s",
        "_resolver",
        "_routes",
        "_secret",
        "_sleep",
        "_transport",
    )

    def __init__(
        self,
        config: ProviderConfiguration,
        transport: HttpTransport,
        network: NetworkBroker,
        secret: SecretBroker,
        resolver: GrantResolver,
        routes: Mapping[str, ApprovedReplicateRoute],
        *,
        clock: Callable[[], int],
        sleep: Callable[[float], None] = _noop_sleep,
        poll_interval_s: float = 1.0,
        max_polls: int = 30,
    ) -> None:
        self._config = config
        self._transport = transport
        self._network = network
        self._secret = secret
        self._resolver = resolver
        self._routes = dict(routes)
        self._clock = clock
        self._sleep = sleep
        self._poll_interval_s = poll_interval_s
        self._max_polls = max_polls

    @property
    def provider_name(self) -> str:
        return self._config.provider.value

    def supports(self, model_id: str) -> bool:
        return model_id in self._routes

    def create_and_wait(
        self, request: CallRequest, input_values: Mapping[str, object]
    ) -> ReplicatePrediction:
        rk = request.route_key
        model_id = rk.split(":", 1)[1] if ":" in rk else rk
        route = self._routes.get(model_id)
        if route is None:
            return ReplicatePrediction(
                "",
                "",
                PredictionState.FAILED,
                error_code=ProviderErrorCode.MODEL_MISSING.value,
                reason=f"model {model_id!r} not in approved pinned routes",
            )
        unknown = [k for k in input_values if k not in route.input_schema_keys]
        if unknown:
            return ReplicatePrediction(
                "",
                route.version_id,
                PredictionState.FAILED,
                error_code=ProviderErrorCode.MALFORMED_OUTPUT.value,
                reason=f"input keys not in approved schema: {sorted(unknown)}",
            )
        grant = self._resolver.resolve(request.task_id)
        if grant is None:
            return ReplicatePrediction(
                "",
                route.version_id,
                PredictionState.FAILED,
                error_code=ProviderErrorCode.NETWORK_DENIED.value,
                reason="no task-scoped CLOUD_ALLOWED grant; prediction refused",
            )
        brokered = BrokeredHttp(
            self._transport,
            BrokeredContext(
                task_id=request.task_id,
                privacy=grant.privacy,
                network=self._network,
                approval=grant.approval,
                secret=self._secret,
                secret_ref=grant.secret_ref,
                now=self._clock(),
                auth_scheme="Token",
            ),
        )
        started = self._clock()
        try:
            prediction_id, state = self._create(brokered, route, dict(input_values))
            state, outputs = self._poll(brokered, route, prediction_id, state)
            return ReplicatePrediction(
                prediction_id,
                route.version_id,
                state,
                outputs=outputs,
                reason="ok" if state is PredictionState.SUCCEEDED else state.value,
                started_at=started,
                finished_at=self._clock(),
            )
        except ProviderError as exc:
            return ReplicatePrediction(
                "",
                route.version_id,
                PredictionState.FAILED,
                error_code=exc.code.value,
                reason=brokered.redact(exc.detail),
                started_at=started,
                finished_at=self._clock(),
            )

    def _create(
        self, brokered: BrokeredHttp, route: ApprovedReplicateRoute, input_values: dict[str, object]
    ) -> tuple[str, PredictionState]:
        body = json.dumps({"version": route.version_id, "input": input_values}).encode("utf-8")
        response = brokered.request(
            "POST",
            f"{self._config.base_url}/predictions",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        if response.status not in (200, 201):
            raise ProviderError(map_http_status(response.status), f"create HTTP {response.status}")
        data = self._json(response, brokered)
        returned_version = str(data.get("version", ""))
        if returned_version and returned_version != route.version_id:
            raise ProviderError(
                ProviderErrorCode.PROVIDER_CONFLICT,
                f"version drift: pinned {route.version_id!r}, got {returned_version!r}",
            )
        return str(data.get("id", "")), self._state(data)

    def _poll(
        self,
        brokered: BrokeredHttp,
        route: ApprovedReplicateRoute,
        prediction_id: str,
        state: PredictionState,
    ) -> tuple[PredictionState, tuple[str, ...]]:
        outputs: tuple[str, ...] = ()
        polls = 0
        while state not in _TERMINAL:
            if polls >= self._max_polls:
                self._cancel(brokered, prediction_id)
                return PredictionState.CANCELED, ()
            self._sleep(self._poll_interval_s)
            polls += 1
            response = brokered.request(
                "GET", f"{self._config.base_url}/predictions/{prediction_id}"
            )
            if response.status != 200:
                raise ProviderError(map_http_status(response.status), f"poll {response.status}")
            data = self._json(response, brokered)
            state = self._state(data)
            if state is PredictionState.SUCCEEDED:
                outputs = self._normalize_output(route, data.get("output"))
        return state, outputs

    def _cancel(self, brokered: BrokeredHttp, prediction_id: str) -> None:
        brokered.request("POST", f"{self._config.base_url}/predictions/{prediction_id}/cancel")

    def cancel(self, request: CallRequest) -> bool:
        self._secret.revoke_task(request.task_id)
        return False

    def _state(self, data: dict[str, object]) -> PredictionState:
        raw = str(data.get("status", ""))
        try:
            return PredictionState(raw)
        except ValueError as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_OUTPUT, f"unknown prediction status {raw!r}"
            ) from exc

    def _normalize_output(self, route: ApprovedReplicateRoute, output: object) -> tuple[str, ...]:
        items = output if isinstance(output, list) else [output]
        normalized: list[str] = []
        for item in items:
            if not isinstance(item, str):
                raise ProviderError(
                    ProviderErrorCode.MALFORMED_OUTPUT, "output element outside approved normalizer"
                )
            if "://" in item:
                host = urlsplit(item).hostname or ""
                if host not in route.approved_output_domains:
                    raise ProviderError(
                        ProviderErrorCode.OUTPUT_URL_DENIED, f"output URL host not approved: {host}"
                    )
            normalized.append(item)
        return tuple(normalized)

    def _json(self, response: HttpResponse, brokered: BrokeredHttp) -> dict[str, object]:
        try:
            data = json.loads(response.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProviderError(
                ProviderErrorCode.MALFORMED_OUTPUT, brokered.redact(str(exc))
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(ProviderErrorCode.MALFORMED_OUTPUT, "prediction not a JSON object")
        return data
