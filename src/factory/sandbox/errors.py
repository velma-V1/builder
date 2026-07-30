"""Typed error for the PH-5 sandbox subsystem (Section 5, Task 5.2)."""

from __future__ import annotations


class SandboxError(Exception):
    code: str
    message: str
    security: bool

    def __init__(self, code: str, message: str, *, security: bool = False) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message
        self.security = security

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"SandboxError(code={self.code!r}, message={self.message!r}, "
            f"security={self.security!r})"
        )
