"""Isolated command-execution boundary for worker-controlled verification input."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class IsolatedCommandRunner(Protocol):
    """Run a verifier command in isolation, never in the Builder host process."""

    def run(self, argv: tuple[str, ...], *, cwd: Path, timeout_s: int) -> CommandResult: ...


@dataclass(frozen=True, slots=True)
class DockerIsolatedCommandRunner:
    """Execute against an ephemeral copy in a hardened, networkless container."""

    image: str

    def run(self, argv: tuple[str, ...], *, cwd: Path, timeout_s: int) -> CommandResult:
        docker = shutil.which("docker")
        if docker is None:
            raise RuntimeError("Docker isolation runtime is unavailable")
        with tempfile.TemporaryDirectory(prefix="builder-verification-") as temporary:
            isolated_copy = Path(temporary) / "workspace"
            # Preserve links instead of following them: worker output must never make the
            # verifier copy arbitrary host files into its execution sandbox.
            shutil.copytree(cwd, isolated_copy, symlinks=True)
            command = [
                docker,
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "128",
                "--memory",
                "2g",
                "--cpus",
                "2",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=512m",  # noqa: S108 - container-internal tmpfs
                "--volume",
                f"{isolated_copy}:/workspace:rw",
                "--workdir",
                "/workspace",
                self.image,
                *argv,
            ]
            try:
                completed = subprocess.run(  # noqa: S603 - fixed Docker security envelope
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env={"PATH": "/usr/local/bin:/usr/bin:/bin"},
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError(f"isolated command exceeded {timeout_s}s") from exc
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


__all__ = ["CommandResult", "DockerIsolatedCommandRunner", "IsolatedCommandRunner"]
