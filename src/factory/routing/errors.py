"""Typed error for the PH-4 model & coding-tool routing subsystem.

``RoutingError`` signals a *contract* or *policy* violation the caller must not paper over
(unapproved model identity, silent-substitution attempt, over-committed reservation, expanded
scope). It never signals a mere runtime outage: a provider being down is an explicit
``RuntimeStatus.UNAVAILABLE`` *result*, not an exception (01J §1, §3.2). Mirrors the code/message
shape used across the security-spine subsystems.
"""

from __future__ import annotations


class RoutingError(Exception):
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
