"""Read-only live-gate readiness runner (Stage-3 preparation).

Runs **only** read-only probes — ``--version`` / ``list`` / ``status`` style queries and Python
stdlib inspection — resolves each tool by absolute path (absent ⇒ ``UNAVAILABLE``), applies a short
timeout, and rolls the findings into a redacted :class:`ReadinessReport`. It writes the report to a
git-ignored directory and exits non-zero if any *mandatory* gate is not ``PASS``.

It never installs, starts, configures, pulls, or upgrades anything. On the Linux builder container
the host tools are absent, so mandatory checks report ``UNAVAILABLE`` and the runner exits non-zero
— the honest result: this container is not the WSL2 live target. The authoritative run happens on
the operator's host.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from factory.livegate.models import CheckStatus, ReadinessCheck, ReadinessReport  # noqa: E402
from factory.livegate.redaction import redact_pairs, redact_text  # noqa: E402
from factory.livegate.sqlite_compliance import (  # noqa: E402
    durable_activation_fails_closed_below_floor,
    evaluate_sqlite_compliance,
)
from factory.livegate.version_probe import (  # noqa: E402
    evaluate_docker,
    evaluate_nvidia,
    evaluate_ollama_models,
    evaluate_wsl,
    parse_ollama_list,
)

OUT_DIR = ROOT / ".livegate-out"
_TIMEOUT_S = 10


def _decode_console_bytes(raw: bytes) -> str:
    """Decode subprocess output that may be UTF-16LE (Windows console tools, e.g. ``wsl.exe``).

    ``wsl.exe`` writes its console output as UTF-16LE. Capturing it with ``text=True`` lets Python
    pick the platform-default codec, which on Windows is a legacy single-byte codepage rather than
    UTF-16 — every other byte decodes as a spurious character and the real ASCII content (e.g.
    ``"Default Version: 2"``) is destroyed. Decoding the raw bytes explicitly, with a UTF-16LE BOM
    check and a NUL-density heuristic for BOM-less UTF-16LE, recovers the intended text.
    """
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace")
    if raw and raw.count(b"\x00") > len(raw) // 4:
        try:
            return raw.decode("utf-16-le", errors="strict")
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def _read_only_command(argv: list[str]) -> str | None:
    """Run a read-only command by absolute path; return stdout, or None if unavailable/failed."""
    exe = shutil.which(argv[0])
    if exe is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 - fixed, read-only args; resolved absolute exe
            [exe, *argv[1:]],
            capture_output=True,
            timeout=_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return _decode_console_bytes(result.stdout) + _decode_console_bytes(result.stderr)


def _host_inventory() -> ReadinessCheck:
    facts = redact_pairs(
        (
            ("system", platform.system()),
            ("release", platform.release()),
            ("machine", platform.machine()),
            ("python", platform.python_version()),
            ("processor", platform.processor() or "unknown"),
        )
    )
    return ReadinessCheck(
        "host-inventory",
        "Host/environment inventory captured",
        CheckStatus.PASS,
        f"discovered on {platform.system()} (advisory baseline; target host is WSL2)",
        mandatory=False,
        facts=facts,
    )


def _docker() -> ReadinessCheck:
    out = _read_only_command(["docker", "--version"])
    return evaluate_docker(out or "")


def _wsl() -> ReadinessCheck:
    out = _read_only_command(["wsl", "--status"])
    return evaluate_wsl(out or "")


def _nvidia() -> ReadinessCheck:
    out = _read_only_command(["nvidia-smi"])
    return evaluate_nvidia(out or "")


def _ollama() -> ReadinessCheck:
    out = _read_only_command(["ollama", "list"])
    if out is None:
        return evaluate_ollama_models(())
    return evaluate_ollama_models(parse_ollama_list(out))


def _sqlite() -> ReadinessCheck:
    check = evaluate_sqlite_compliance()
    # Independent confirmation that a below-floor engine cannot silently activate a durable store.
    if not durable_activation_fails_closed_below_floor():  # pragma: no cover - guard is unit-tested
        return ReadinessCheck(
            check.check_id,
            check.title,
            CheckStatus.ERROR,
            "durable-store guard did NOT fail closed below floor — investigate before any live use",
            mandatory=True,
            facts=check.facts,
        )
    return check


def build_report() -> ReadinessReport:
    checks = (
        _sqlite(),  # first mandatory gate
        _host_inventory(),
        _docker(),
        _wsl(),
        _nvidia(),
        _ollama(),
    )
    return ReadinessReport(environment="live-gate-target (hostname redacted)", checks=checks)


def _write_output(report: ReadinessReport) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "environment": redact_text(report.environment),
        "ready": report.ready,
        "checks": [asdict(c) for c in report.checks],
    }
    out_path = OUT_DIR / "readiness.json"
    out_path.write_text(redact_text(json.dumps(payload, indent=2)), encoding="utf-8")
    return out_path


def main() -> int:
    report = build_report()
    out_path = _write_output(report)
    print("=" * 78)
    print("LIVE-GATE READINESS (read-only preparation probe — no host changes made)")
    print("=" * 78)
    for check in report.checks:
        flag = "MUST" if check.mandatory else "----"
        print(f"[{flag}] {check.status.value:<12} {check.check_id:<16} {check.detail}")
    print("-" * 78)
    print(f"redacted report: {out_path.relative_to(ROOT)}")
    if report.ready:
        print("READY: all mandatory gates PASS.")
        return 0
    blockers = ", ".join(c.check_id for c in report.blocking_failures)
    print(f"NOT READY (expected off the live host): blocking gates → {blockers}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
