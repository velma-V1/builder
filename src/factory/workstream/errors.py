"""Typed error for the PH-6 workstream subsystem (Section 6)."""

from __future__ import annotations


class WorkstreamError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"WorkstreamError(code={self.code!r}, message={self.message!r})"
