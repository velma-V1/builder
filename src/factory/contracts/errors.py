from __future__ import annotations

from factory.contracts.models import ErrorCode, ValidationIssue


class ContractError(Exception):
    code: ErrorCode
    message: str
    issues: tuple[ValidationIssue, ...]

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        issues: tuple[ValidationIssue, ...] = (),
    ) -> None:
        super().__init__(code, message)
        self.code = code
        self.message = message
        self.issues = issues

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, message={self.message!r}, "
            f"issues={self.issues!r})"
        )
