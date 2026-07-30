"""Typed error for the PH-6 integration coordinator (Section 6, Task 6.5)."""

from __future__ import annotations


class IntegrationError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"IntegrationError(code={self.code!r}, message={self.message!r})"
