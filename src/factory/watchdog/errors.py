"""Typed failures for CMP-WATCH and its internal intervention receiver."""

from __future__ import annotations


class WatchdogError(Exception):
    """Fail-closed Watchdog error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


__all__ = ["WatchdogError"]
