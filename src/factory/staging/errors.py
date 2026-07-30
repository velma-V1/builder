"""Typed error for the PH-5 quarantined-staging subsystem (Section 5, Task 5.4)."""

from __future__ import annotations


class StagingError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"StagingError(code={self.code!r}, message={self.message!r})"
