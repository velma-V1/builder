"""Typed error for the PH-5 cache subsystem (Section 5, Task 5.4)."""

from __future__ import annotations


class CacheError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"CacheError(code={self.code!r}, message={self.message!r})"
