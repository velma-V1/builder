from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from factory.contracts.errors import ContractError
from factory.contracts.models import ErrorCode

_RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{digit}" for digit in "123456789"}
    | {f"LPT{digit}" for digit in "123456789"}
)

_WRITE_LIKE_OPERATIONS = frozenset({"write", "create", "modify", "delete"})


@dataclass(frozen=True, slots=True)
class PathAuthorityResult:
    allowed: bool
    normalized_relative: str
    resolved_path: Path
    reason: str
    requires_serialization: bool


def _segment_pattern(segment: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in segment.split("*")]
    return re.compile("^" + "[^/]*".join(parts) + "$")


def _match_glob_segments(pattern: Sequence[str], candidate: Sequence[str]) -> bool:
    if not pattern:
        return not candidate
    head, rest = pattern[0], pattern[1:]
    if head == "**":
        if _match_glob_segments(rest, candidate):
            return True
        return bool(candidate) and _match_glob_segments(pattern, candidate[1:])
    if not candidate:
        return False
    if _segment_pattern(head).match(candidate[0]):
        return _match_glob_segments(rest, candidate[1:])
    return False


def _matches_glob(pattern: str, normalized_relative: str) -> bool:
    pattern_segments = [segment for segment in pattern.split("/") if segment]
    candidate_segments = [segment for segment in normalized_relative.split("/") if segment]
    return _match_glob_segments(pattern_segments, candidate_segments)


def _matches_any(patterns: Sequence[str], normalized_relative: str) -> bool:
    return any(_matches_glob(pattern, normalized_relative) for pattern in patterns)


def _reject_unsafe_syntax(candidate: str) -> None:
    if "\x00" in candidate:
        raise ContractError(ErrorCode.SECURITY_DENIED, "path contains a null byte")
    if not candidate:
        raise ContractError(ErrorCode.SECURITY_DENIED, "path is empty")
    if candidate.startswith(("/", "\\")) or candidate.startswith(("//", "\\\\")):
        raise ContractError(ErrorCode.SECURITY_DENIED, "absolute paths are rejected")
    if re.match(r"^[A-Za-z]:", candidate):
        raise ContractError(ErrorCode.SECURITY_DENIED, "drive-qualified paths are rejected")
    if ":" in candidate:
        raise ContractError(
            ErrorCode.SECURITY_DENIED, "colon path components (e.g. NTFS ADS) are rejected"
        )

    normalized = candidate.replace("\\", "/")
    segments = normalized.split("/")
    for segment in segments:
        if segment in ("", "."):
            continue
        if segment == "..":
            raise ContractError(ErrorCode.SECURITY_DENIED, "path traversal ('..') is rejected")
        if segment != segment.rstrip(" ."):
            raise ContractError(
                ErrorCode.SECURITY_DENIED, "trailing spaces or dots in path segments are rejected"
            )
        bare_name = segment.split(".", 1)[0].upper()
        if bare_name in _RESERVED_DEVICE_NAMES:
            message = f"reserved device name rejected: {segment}"
            raise ContractError(ErrorCode.SECURITY_DENIED, message)


def _normalize(candidate: str) -> str:
    _reject_unsafe_syntax(candidate)
    normalized = candidate.replace("\\", "/")
    segments = [segment for segment in normalized.split("/") if segment and segment != "."]
    return "/".join(segments)


@dataclass(slots=True)
class PathAuthority:
    project_root: Path

    def _resolve(self, normalized_relative: str) -> Path:
        root = self.project_root.resolve()
        current = root
        remaining = normalized_relative.split("/") if normalized_relative else []
        index = 0
        while index < len(remaining):
            candidate = current / remaining[index]
            if candidate.exists():
                current = candidate.resolve()
                index += 1
            else:
                break
        for segment in remaining[index:]:
            current = current / segment
        return current

    def _is_contained(self, root: Path, resolved: Path) -> bool:
        root_str = os.path.normcase(str(root))
        resolved_str = os.path.normcase(str(resolved))
        common = os.path.commonpath([root_str, resolved_str])
        return common == root_str

    def evaluate(
        self,
        candidate: str,
        *,
        operation: str,
        allowed: Sequence[str],
        forbidden: Sequence[str],
        read_only: Sequence[str],
        active_exclusive_paths: Sequence[str],
    ) -> PathAuthorityResult:
        try:
            normalized_relative = _normalize(candidate)
        except ContractError as exc:
            return PathAuthorityResult(
                allowed=False,
                normalized_relative="",
                resolved_path=self.project_root,
                reason=exc.message,
                requires_serialization=False,
            )

        resolved_path = self._resolve(normalized_relative)
        root = self.project_root.resolve()

        if not self._is_contained(root, resolved_path):
            return PathAuthorityResult(
                allowed=False,
                normalized_relative=normalized_relative,
                resolved_path=resolved_path,
                reason="path escapes the project root",
                requires_serialization=False,
            )

        if _matches_any(forbidden, normalized_relative):
            return PathAuthorityResult(
                allowed=False,
                normalized_relative=normalized_relative,
                resolved_path=resolved_path,
                reason="path matches a forbidden path class",
                requires_serialization=False,
            )

        if operation in _WRITE_LIKE_OPERATIONS and _matches_any(read_only, normalized_relative):
            return PathAuthorityResult(
                allowed=False,
                normalized_relative=normalized_relative,
                resolved_path=resolved_path,
                reason="path is read-only for this operation",
                requires_serialization=False,
            )

        if operation in _WRITE_LIKE_OPERATIONS and _matches_any(
            active_exclusive_paths, normalized_relative
        ):
            return PathAuthorityResult(
                allowed=False,
                normalized_relative=normalized_relative,
                resolved_path=resolved_path,
                reason="path is under an active exclusive ownership lease",
                requires_serialization=False,
            )

        if not _matches_any(allowed, normalized_relative):
            return PathAuthorityResult(
                allowed=False,
                normalized_relative=normalized_relative,
                resolved_path=resolved_path,
                reason="path does not match any allowed path class",
                requires_serialization=False,
            )

        return PathAuthorityResult(
            allowed=True,
            normalized_relative=normalized_relative,
            resolved_path=resolved_path,
            reason="path is allowed",
            requires_serialization=False,
        )

    def revalidate_before_use(self, previous: PathAuthorityResult) -> None:
        if not previous.allowed:
            raise ContractError(ErrorCode.SECURITY_DENIED, "cannot use a previously denied path")
        fresh = self._resolve(previous.normalized_relative)
        if fresh != previous.resolved_path:
            raise ContractError(
                ErrorCode.SECURITY_DENIED,
                "path resolution changed since authorization (possible TOCTOU)",
            )
        root = self.project_root.resolve()
        if not self._is_contained(root, fresh):
            raise ContractError(ErrorCode.SECURITY_DENIED, "path escapes the project root")
