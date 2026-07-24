from __future__ import annotations

from dataclasses import dataclass

from factory.contracts.models import ErrorCode, ValidationIssue


@dataclass(frozen=True, slots=True)
class ContractError(Exception):
    code: ErrorCode
    message: str
    issues: tuple[ValidationIssue, ...] = ()

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
