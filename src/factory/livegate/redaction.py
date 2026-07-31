"""Redaction for readiness output.

Host inventory naturally surfaces user names, home paths, tokens, and IPs. The discovery output is
written to a git-ignored location, but redaction is applied *before* anything is written or logged
so a copy pasted into a review comment cannot leak. The rules are deliberately conservative — it is
acceptable to over-redact a readiness report; it is never acceptable to leak a credential.
"""

from __future__ import annotations

import re

_TOKEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # PEM private-key blocks.
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED_PRIVATE_KEY]"),
    # Common cloud / VCS token shapes.
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY_ID]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED_TOKEN]"),
    # key=value secrets (token / secret / password / api_key). Group 1 keeps the key + separator;
    # the value (group 2) is masked.
    (re.compile(r"(?i)\b([a-z0-9_]*(?:token|secret|password|passwd|api[_-]?key)\s*[=:]\s*)"
                r"(\"[^\"]+\"|'[^']+'|\S+)"),
     r"\1[REDACTED]"),
)

_HOME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"/home/[^/\s:]+"), "/home/[USER]"),
    (re.compile(r"/Users/[^/\s:]+"), "/Users/[USER]"),
    (re.compile(r"C:\\Users\\[^\\\s:]+", re.I), r"C:\\Users\\[USER]"),
)

# Public/documentation IPs and infra literals are preserved as-is where useful, but any other
# routable IPv4 literal is masked to its /16 so topology is legible without pinpointing a host.
_IPV4 = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")
# Redaction allowlist (not bind addresses); "0.0.0.0" is a literal to preserve verbatim.
_IP_ALLOW = frozenset(
    {"127.0.0.1", "0.0.0.0", "169.254.169.254", "255.255.255.255"}  # noqa: S104
)


def _mask_ip(match: re.Match[str]) -> str:
    whole = match.group(0)
    if whole in _IP_ALLOW:
        return whole
    return f"{match.group(1)}.{match.group(2)}.x.x"


def redact_text(text: str) -> str:
    """Return ``text`` with credentials, home paths, and host IPs masked."""
    out = text
    for pattern, replacement in _TOKEN_PATTERNS:
        out = pattern.sub(replacement, out)
    for pattern, replacement in _HOME_PATTERNS:
        out = pattern.sub(replacement, out)
    out = _IPV4.sub(_mask_ip, out)
    return out


def redact_pairs(pairs: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    """Redact the value side of ``(key, value)`` fact pairs."""
    return tuple((key, redact_text(value)) for key, value in pairs)
