"""Phase 3B requirements 8/9: staged output (STAGED_WRITE) and sandboxed output
(SANDBOXED_EXECUTION) must both funnel through the same real, existing quarantine/inspection gate
(``factory.staging.QuarantinedStaging``) before promotion -- neither mode gets a shortcut.

This uses the real PH-5 staging primitive (no mock), since that gate already exists and Phase 3B
depends on it rather than reimplementing or bypassing it. Full end-to-end wiring through
WorkerEngineService's verification/approval pipeline is part of the continued Phase 3B
implementation (not yet built at the time of this correction); these tests prove the underlying
gate Phase 3B will drive is real and cannot be bypassed by either write-capable mode.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from factory.staging.errors import StagingError
from factory.staging.manager import QuarantinedStaging
from factory.staging.models import StagedFile


def _staging(tmp_path: Path, approved_scope: tuple[str, ...] = ("src/**",)) -> QuarantinedStaging:
    return QuarantinedStaging("staging-1", tmp_path, approved_scope)


def test_staged_write_output_cannot_be_promoted_without_authorization(tmp_path: Path) -> None:
    """STAGED_WRITE output: clean (in-scope, no findings) but unauthorized must still be denied."""
    staging = _staging(tmp_path)
    staging.stage(StagedFile(path="src/foo.py", content=b"print('hi')\n", provenance="worker"))

    with pytest.raises(StagingError) as excinfo:
        staging.promote(authorized=False)
    assert excinfo.value.code == "PROMOTION_UNAUTHORIZED"


def test_sandboxed_execution_output_cannot_be_promoted_without_authorization(
    tmp_path: Path,
) -> None:
    """SANDBOXED_EXECUTION output goes through the identical gate -- no shortcut for the more
    trusted-sounding mode."""
    staging = _staging(tmp_path)
    staging.stage(
        StagedFile(path="src/bar.py", content=b"def f(): pass\n", provenance="sandboxed-worker")
    )

    with pytest.raises(StagingError) as excinfo:
        staging.promote(authorized=False)
    assert excinfo.value.code == "PROMOTION_UNAUTHORIZED"


def test_out_of_scope_staged_output_is_blocked_regardless_of_authorization(
    tmp_path: Path,
) -> None:
    """Even a caller that WOULD authorize promotion cannot promote output outside the approved
    scope -- inspection findings block promotion before authorization is even consulted."""
    staging = _staging(tmp_path, approved_scope=("src/**",))
    staging.stage(
        StagedFile(path="secrets/credentials.txt", content=b"token=abc", provenance="worker")
    )

    with pytest.raises(StagingError) as excinfo:
        staging.promote(authorized=True)
    assert excinfo.value.code == "STAGING_UNCLEAN"


def test_path_escaping_staged_output_is_blocked_regardless_of_authorization(
    tmp_path: Path,
) -> None:
    staging = _staging(tmp_path)
    staging.stage(StagedFile(path="../../etc/passwd", content=b"root:x:0:0", provenance="worker"))

    with pytest.raises(StagingError) as excinfo:
        staging.promote(authorized=True)
    assert excinfo.value.code == "STAGING_UNCLEAN"


def test_clean_and_authorized_staged_output_promotes_successfully(tmp_path: Path) -> None:
    """The gate is not merely restrictive -- clean, in-scope, explicitly authorized output is the
    one path that DOES succeed, proving the gate discriminates rather than blocking everything."""
    staging = _staging(tmp_path)
    staging.stage(StagedFile(path="src/ok.py", content=b"x = 1\n", provenance="worker"))

    result = staging.promote(authorized=True)
    assert result.promoted is True


def test_a_promoted_staging_area_cannot_be_staged_into_again(tmp_path: Path) -> None:
    """Once promoted, the quarantine area is sealed -- an attempt to slip more (unreviewed)
    content in afterward is rejected, not silently accepted."""
    staging = _staging(tmp_path)
    staging.stage(StagedFile(path="src/ok.py", content=b"x = 1\n", provenance="worker"))
    staging.promote(authorized=True)

    with pytest.raises(StagingError) as excinfo:
        staging.stage(StagedFile(path="src/more.py", content=b"y = 2\n", provenance="worker"))
    assert excinfo.value.code == "STAGING_SEALED"
