"""Compatibility negotiation between Builder's contract and a reported Agent Zero worker version.

Pure and deterministic: given the pinned contract version Builder speaks and the version a worker
reports, decide whether the pairing is safe to use. An unrecognized or newer-major worker report is
rejected, never silently accepted — a worker cannot upgrade Builder's expectations of it.
"""

from __future__ import annotations

from factory.integrations.agent_zero.models import CompatibilityReport


def _parse(version: str) -> tuple[int, int, int] | None:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def check_compatibility(
    *, builder_contract_version: str, worker_reported_version: str
) -> CompatibilityReport:
    """PASS only when major versions match and the worker is not ahead in minor/patch.

    A worker reporting an unparseable version, a different major version, or a newer minor/patch
    than Builder's contract is rejected — Builder never adapts itself to an unrecognized worker.
    """
    contract = _parse(builder_contract_version)
    reported = _parse(worker_reported_version)
    if contract is None:
        return CompatibilityReport(
            builder_contract_version,
            worker_reported_version,
            compatible=False,
            reason="builder_contract_version is unparseable (internal defect)",
        )
    if reported is None:
        return CompatibilityReport(
            builder_contract_version,
            worker_reported_version,
            compatible=False,
            reason="worker_reported_version is unparseable",
        )
    if reported[0] != contract[0]:
        return CompatibilityReport(
            builder_contract_version,
            worker_reported_version,
            compatible=False,
            reason=f"major version mismatch: builder={contract[0]} worker={reported[0]}",
        )
    if reported > contract:
        return CompatibilityReport(
            builder_contract_version,
            worker_reported_version,
            compatible=False,
            reason="worker reports a version newer than Builder's pinned contract",
        )
    return CompatibilityReport(
        builder_contract_version,
        worker_reported_version,
        compatible=True,
        reason="compatible",
    )
