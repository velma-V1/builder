"""Authenticated OpenAI-compatible facade over Builder's deterministic model router."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from factory.integrations.agent_zero.policy import AgentZeroCapabilityRequest, ModelRouterPort


class ModelGatewayError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModelGateway:
    router: ModelRouterPort
    credential: str
    selected_model: str
    max_prompt_chars: int = 200_000
    selected_provider_route: str = "ollama:local"

    def complete(self, authorization: str, payload: object) -> dict[str, object]:
        expected = f"Bearer {self.credential}"
        if not secrets.compare_digest(authorization, expected):
            raise ModelGatewayError("model gateway authentication failed")
        if not isinstance(payload, dict) or payload.get("stream") is True:
            raise ModelGatewayError("streaming or malformed model requests are unsupported")
        if payload.get("model") != self.selected_model:
            raise ModelGatewayError("requested model is not the selected Builder route")
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ModelGatewayError("messages are required")
        parts: list[str] = []
        for message in messages:
            if not isinstance(message, dict):
                raise ModelGatewayError("message is malformed")
            role, content = message.get("role"), message.get("content")
            if not isinstance(role, str) or not isinstance(content, str):
                raise ModelGatewayError("message role/content must be strings")
            parts.append(f"{role}: {content}")
        prompt = "\n".join(parts)
        if len(prompt) > self.max_prompt_chars:
            raise ModelGatewayError("model request exceeds prompt ceiling")
        result = self.router.request(
            AgentZeroCapabilityRequest("agent-zero", "chat_completion", prompt)
        )
        if not result.ok:
            raise ModelGatewayError(result.reason or "selected Builder model is unavailable")
        if result.provider_route != self.selected_provider_route:
            raise ModelGatewayError("Builder router attempted an unauthorized model substitution")
        return {
            "id": f"builder-{result.model_fingerprint[:16]}",
            "object": "chat.completion",
            "model": self.selected_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result.output},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


__all__ = ["ModelGateway", "ModelGatewayError"]
