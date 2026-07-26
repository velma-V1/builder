"""Typed error for the roadmap PH-3 audit subsystem (CMP-AUDITW / CMP-AUDITV)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
