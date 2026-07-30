#!/usr/bin/env python3
"""Run the full Section 1 verification pipeline and record an evidence manifest.

Executes, in order: uv sync, ruff format check, ruff lint, strict mypy, unit tests,
integration tests, security tests, failure-path tests, and the full suite with a
95% branch-coverage gate. Every command's exit code, stdout/stderr hashes, and
timing are recorded to artifacts/verification/section-1/manifest.json, alongside
environment identity (Python version, OS, git commit, dependency lock hash).
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "artifacts" / "verification" / "section-1" / "manifest.json"

COMMANDS: list[list[str]] = [
    ["uv", "sync", "--frozen"],
    ["uv", "run", "ruff", "format", "--check", "src", "tests", "scripts"],
    ["uv", "run", "ruff", "check", "src", "tests", "scripts"],
    ["uv", "run", "mypy", "src/factory/contracts"],
    ["uv", "run", "pytest", "tests/contracts/unit", "-v"],
    ["uv", "run", "pytest", "tests/contracts/integration", "-v"],
    ["uv", "run", "pytest", "tests/contracts/security", "-m", "security", "-v"],
    ["uv", "run", "pytest", "tests/contracts/failure_paths", "-m", "failure_path", "-v"],
    [
        "uv",
        "run",
        "pytest",
        "tests/contracts",
        "--cov=src/factory/contracts",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=95",
    ],
]


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    started_at: str
    ended_at: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(command: list[str]) -> tuple[CommandResult, str, str]:
    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    completed = subprocess.run(  # noqa: S603 -- fixed, hardcoded verification commands only
        command, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    ended_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = CommandResult(
        command=" ".join(command),
        started_at=started_at,
        ended_at=ended_at,
        exit_code=completed.returncode,
        stdout_sha256=_sha256(completed.stdout.encode("utf-8")),
        stderr_sha256=_sha256(completed.stderr.encode("utf-8")),
    )
    return result, completed.stdout, completed.stderr


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607 -- fixed, hardcoded command only
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or "unknown"


def _dependency_lock_hash() -> str:
    lock_path = REPO_ROOT / "uv.lock"
    if not lock_path.is_file():
        return "missing"
    return _sha256(lock_path.read_bytes())


def main() -> int:
    results: list[CommandResult] = []
    overall_exit_code = 0

    for command in COMMANDS:
        result, stdout, stderr = _run(command)
        results.append(result)
        print(f"$ {result.command}")
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        print(f"[exit code {result.exit_code}]\n")
        if result.exit_code != 0:
            overall_exit_code = result.exit_code
            break

    manifest = {
        "environment": {
            "python_version": platform.python_version(),
            "os_version": platform.platform(),
            "git_commit": _git_commit(),
            "dependency_lock_sha256": _dependency_lock_hash(),
        },
        "commands": [asdict(result) for result in results],
        "overall_exit_code": overall_exit_code,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return overall_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
