"""Typed error for the PH-5 Git manager (Section 5, Task 5.1).

``GitError`` signals a policy or contract violation (protected-ref write, force-push attempt,
unexplained local changes, trailer mismatch, out-of-scope checkpoint). A ``security`` flag marks
violations that ``01I §3.2`` requires to be recorded as security events.
"""

from __future__ import annotations


class GitError(Exception):
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
        return f"GitError(code={self.code!r}, message={self.message!r}, security={self.security!r})"
