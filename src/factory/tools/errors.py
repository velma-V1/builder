"""Typed error for the roadmap PH-3 tool subsystem (CMP-TOOLREG / CMP-TOOLGW)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
