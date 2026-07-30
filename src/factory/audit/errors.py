"""Typed error for the roadmap PH-3 audit subsystem (CMP-AUDITW / CMP-AUDITV)."""

from __future__ import annotations


class AuditError(Exception):
    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"
