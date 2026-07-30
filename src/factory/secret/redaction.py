"""Secret redaction (``01E §3.4``).

Deterministic replacement of secret material in arbitrary text (commands, logs, evidence, exports).
Longer secrets are redacted first so a secret that contains another is not partially revealed.
"""

from __future__ import annotations

from collections.abc import Iterable

REDACTED = "***REDACTED***"


def redact(text: str, values: Iterable[str]) -> str:
    for value in sorted({v for v in values if v}, key=len, reverse=True):
        text = text.replace(value, REDACTED)
    return text


def contains_secret(text: str, values: Iterable[str]) -> bool:
    return any(value and value in text for value in values)
