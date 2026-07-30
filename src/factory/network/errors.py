"""Typed error for the PH-5 network broker (Section 5, Task 5.3)."""

from __future__ import annotations


class NetworkError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"NetworkError(code={self.code!r}, message={self.message!r})"
