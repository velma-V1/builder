"""A real, minimal Ollama HTTP client (Phase 3B).

``factory.models.ollama_adapter.fake_ollama`` is the deterministic fake this codebase already
relies on for tests; this module is its live counterpart, used only by the Worker Engine's
Ollama+Devstral integration and the explicitly-labeled live integration check
(``scripts/check_ollama_devstral.py``). Stdlib-only (``urllib.request``, no new dependency),
mirroring the same argument-list/no-shell discipline used elsewhere in this repository for
external-process calls, applied here to an outbound loopback HTTP call instead.

Every failure mode is a distinct, typed exception -- never a bare exception escaping to a caller
that can't distinguish "the model doesn't exist" from "Ollama isn't running" from "the model took
too long".
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_TIMEOUT_S = 120
#: The human-facing display name Builder documents/reports everywhere. Never assumed to be the
#: literal Ollama tag string -- Ollama's own tagging convention for this model varies (e.g. this
#: environment installs it as "devstral-small-2:24b", not "devstral-small2:24b" or
#: "devstral:24b") and must always be *discovered*, never guessed. See ``resolve_devstral_tag``.
DEVSTRAL_DISPLAY_NAME = "Devstral Small 2 24B"
#: Substring(s) used to recognize an installed tag as "the Devstral Small 2 model" regardless of
#: the exact hyphenation Ollama's registry uses for it.
_DEVSTRAL_TAG_MARKERS = ("devstral-small-2", "devstral-small2", "devstral_small_2")


class OllamaError(Exception):
    """Base for every typed Ollama client failure."""


class OllamaUnavailable(OllamaError):
    """Ollama is not reachable at all (connection refused, DNS failure, etc.)."""


class OllamaTimeout(OllamaError):
    """The request exceeded its bounded timeout."""


class OllamaModelMissing(OllamaError):
    """The requested model is not present in ``ollama list``."""


class OllamaMalformedResponse(OllamaError):
    """Ollama responded, but the body wasn't the JSON shape this client expects."""


@dataclass(frozen=True, slots=True)
class OllamaGenerateResult:
    model: str
    response_text: str
    done: bool
    total_duration_ns: int | None = None


@dataclass(frozen=True, slots=True)
class ResolvedModel:
    """The display name Builder reports everywhere, kept separate from the literal Ollama tag
    actually resolved on this host -- the two are never assumed to be the same string."""

    display_name: str
    configured_tag: str


class OllamaClient:
    """A real, minimal Ollama HTTP client. No dependency beyond the stdlib."""

    __slots__ = ("_base_url", "_timeout_s")

    def __init__(
        self, *, base_url: str = _DEFAULT_BASE_URL, timeout_s: int = _DEFAULT_TIMEOUT_S
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def list_models(self) -> tuple[str, ...]:
        """Every model tag Ollama currently reports as installed."""
        request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:  # noqa: S310
                body = response.read()
        except urllib.error.URLError as exc:
            raise OllamaUnavailable(f"could not reach Ollama at {self._base_url}: {exc}") from exc
        except TimeoutError as exc:
            raise OllamaTimeout(f"listing models timed out after {self._timeout_s}s") from exc
        try:
            payload = json.loads(body)
            models = payload["models"]
            return tuple(str(entry["name"]) for entry in models)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaMalformedResponse(f"malformed /api/tags response: {exc}") from exc

    def has_model(self, model: str) -> bool:
        """``True`` iff ``model`` (or a `:latest`-normalized match) is installed."""
        installed = self.list_models()
        if model in installed:
            return True
        # Ollama tags default to ":latest" when no tag is given; accept either spelling.
        bare = model.split(":", 1)[0]
        return any(name == model or name.split(":", 1)[0] == bare for name in installed)

    def generate(
        self, *, model: str, prompt: str, timeout_s: int | None = None
    ) -> OllamaGenerateResult:
        """One non-streamed completion call. Raises a typed error for every failure mode."""
        body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/api/generate",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        effective_timeout = self._timeout_s if timeout_s is None else timeout_s
        try:
            with urllib.request.urlopen(request, timeout=effective_timeout) as response:  # noqa: S310
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            if exc.code == 404 or "not found" in detail.lower():
                raise OllamaModelMissing(f"model {model!r} not found: {detail}") from exc
            raise OllamaUnavailable(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OllamaUnavailable(f"could not reach Ollama at {self._base_url}: {exc}") from exc
        except TimeoutError as exc:
            raise OllamaTimeout(f"generate timed out after {effective_timeout}s") from exc

        try:
            payload = json.loads(raw)
            return OllamaGenerateResult(
                model=str(payload["model"]),
                response_text=str(payload["response"]),
                done=bool(payload["done"]),
                total_duration_ns=payload.get("total_duration"),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise OllamaMalformedResponse(f"malformed /api/generate response: {exc}") from exc


def resolve_devstral_tag(client: OllamaClient, *, override_tag: str | None = None) -> ResolvedModel:
    """Discover the exact locally-installed Ollama tag for Devstral Small 2 24B -- never assume
    a hardcoded string, since the same model may be tagged differently across hosts (e.g.
    ``devstral-small-2:24b`` vs ``devstral-small2:24b`` vs ``devstral:24b``).

    ``override_tag`` lets an operator pin an exact tag explicitly (e.g. via configuration); when
    given, it is used as-is (still checked for actual presence via ``has_model``) rather than
    searched for. Raises :class:`OllamaModelMissing` with the full installed-tag list in the
    message if nothing matching is found, so the failure is immediately actionable.
    """
    if override_tag is not None:
        if not client.has_model(override_tag):
            installed = client.list_models()
            raise OllamaModelMissing(
                f"configured model tag {override_tag!r} is not installed; "
                f"installed tags: {list(installed)}"
            )
        return ResolvedModel(display_name=DEVSTRAL_DISPLAY_NAME, configured_tag=override_tag)

    installed = client.list_models()
    for tag in installed:
        lowered = tag.lower()
        if any(marker in lowered for marker in _DEVSTRAL_TAG_MARKERS):
            return ResolvedModel(display_name=DEVSTRAL_DISPLAY_NAME, configured_tag=tag)
    raise OllamaModelMissing(
        f"no installed Ollama tag matched {DEVSTRAL_DISPLAY_NAME!r} "
        f"(looked for a tag containing one of {_DEVSTRAL_TAG_MARKERS}); "
        f"installed tags: {list(installed)}"
    )
