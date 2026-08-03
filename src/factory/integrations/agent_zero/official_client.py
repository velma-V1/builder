"""Client for Agent Zero v2.7's documented, API-key-protected endpoints."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

from factory.providers.transport import HttpRequest, HttpResponse, HttpTransport


class AgentZeroOfficialError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentZeroPoll:
    context_id: str
    running: bool
    response: str | None


@dataclass(frozen=True, slots=True)
class AgentZeroOfficialClient:
    base_url: str
    api_key: str
    transport: HttpTransport
    timeout_s: int
    _csrf_token: str = ""
    _session_cookie: str = ""

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, object] | None = None,
        authenticated: bool = True,
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["X-API-KEY"] = self.api_key
        response = self.transport.send(
            HttpRequest(
                method=method,
                url=self._url(path),
                headers=headers,
                body=json.dumps(payload).encode() if payload is not None else b"",
                timeout_s=float(self.timeout_s),
            )
        )
        return _parse_object(response)

    def probe(self) -> None:
        self._request("GET", "/api/health", authenticated=False)

    def _csrf(self) -> tuple[str, str]:
        response = self.transport.send(
            HttpRequest(
                "GET",
                self._url("/api/csrf_token"),
                headers={"Origin": self.base_url.rstrip("/")},
                timeout_s=float(self.timeout_s),
            )
        )
        data = _parse_object(response)
        token = data.get("token")
        cookie = next(
            (
                value.split(";", 1)[0]
                for key, value in response.headers.items()
                if key.lower() == "set-cookie"
            ),
            "",
        )
        if data.get("ok") is not True or not isinstance(token, str) or not cookie:
            raise AgentZeroOfficialError("Agent Zero CSRF session was not established")
        return token, cookie

    def start_async(self, work_order_json: str) -> str:
        token, cookie = self._csrf()
        response = self.transport.send(
            HttpRequest(
                "POST",
                self._url("/api/message_async"),
                headers={
                    "Content-Type": "application/json",
                    "X-CSRF-Token": token,
                    "Cookie": cookie,
                    "Origin": self.base_url.rstrip("/"),
                },
                body=json.dumps({"text": work_order_json, "context": ""}).encode(),
                timeout_s=float(self.timeout_s),
            )
        )
        data = _parse_object(response)
        context = data.get("context")
        if not isinstance(context, str) or not context:
            raise AgentZeroOfficialError("malformed Agent Zero async context response")
        object.__setattr__(self, "_csrf_token", token)
        object.__setattr__(self, "_session_cookie", cookie)
        return context

    def poll(self, context_id: str) -> AgentZeroPoll:
        if not self._csrf_token or not self._session_cookie:
            token, cookie = self._csrf()
            object.__setattr__(self, "_csrf_token", token)
            object.__setattr__(self, "_session_cookie", cookie)
        response = self.transport.send(
            HttpRequest(
                "POST",
                self._url("/api/poll"),
                headers={
                    "Content-Type": "application/json",
                    "X-CSRF-Token": self._csrf_token,
                    "Cookie": self._session_cookie,
                    "Origin": self.base_url.rstrip("/"),
                },
                body=json.dumps(
                    {
                        "context": context_id,
                        "log_from": 0,
                        "notifications_from": 0,
                        "timezone": "UTC",
                    }
                ).encode(),
                timeout_s=float(self.timeout_s),
            )
        )
        data = _parse_object(response)
        if data.get("context") != context_id or not isinstance(
            data.get("log_progress_active"), bool
        ):
            raise AgentZeroOfficialError("malformed Agent Zero poll response")
        running = bool(data["log_progress_active"])
        answer: str | None = None
        logs = data.get("logs")
        if not running and isinstance(logs, list):
            for item in reversed(logs):
                if isinstance(item, dict) and item.get("type") in {"response", "agent"}:
                    content = item.get("content")
                    if isinstance(content, str):
                        answer = content
                        break
        return AgentZeroPoll(context_id, running, answer)

    def cancel(self, context_id: str) -> bool:
        data = self._request("POST", "/api/api_terminate_chat", payload={"context_id": context_id})
        return data.get("success") is True

    def logs(self, context_id: str, *, length: int = 100) -> tuple[Mapping[str, object], ...]:
        if length <= 0 or length > 1000:
            raise ValueError("length must be between 1 and 1000")
        query = urlencode({"context_id": context_id, "length": length})
        data = self._request("GET", f"/api/api_log_get?{query}")
        log = data.get("log")
        items = log.get("items") if isinstance(log, dict) else None
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise AgentZeroOfficialError("malformed Agent Zero log response")
        return tuple(items)


def _parse_object(response: HttpResponse) -> dict[str, object]:
    if response.status != 200:
        raise AgentZeroOfficialError(f"Agent Zero HTTP {response.status}")
    try:
        parsed = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise AgentZeroOfficialError("malformed Agent Zero JSON response") from exc
    if not isinstance(parsed, dict):
        raise AgentZeroOfficialError("Agent Zero response was not an object")
    return parsed


__all__ = ["AgentZeroOfficialClient", "AgentZeroOfficialError", "AgentZeroPoll"]
