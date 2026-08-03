"""Runtime-only operator session authentication for authority-bearing API actions."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OperatorSession:
    credential: str
    operator: str

    def __post_init__(self) -> None:
        if not self.credential or not self.operator.strip():
            raise ValueError("operator session fields must be non-empty")

    def authenticate(self, authorization: str | None) -> str | None:
        if authorization is None or not authorization.startswith("Bearer "):
            return None
        supplied = authorization.removeprefix("Bearer ")
        return self.operator if secrets.compare_digest(supplied, self.credential) else None


__all__ = ["OperatorSession"]
