"""Stage-3 unit — host readiness parsers and compatibility evaluators."""

from __future__ import annotations

from factory.livegate.models import CheckStatus
from factory.livegate.version_probe import (
    _BOM,
    APPROVED_LOCAL_MODELS,
    _clean_probe_text,
    evaluate_docker,
    evaluate_nvidia,
    evaluate_ollama_models,
    evaluate_wsl,
    parse_docker_version,
    parse_nvidia_smi,
    parse_ollama_list,
)


def test_clean_probe_text_leaves_normal_text_unchanged() -> None:
    assert _clean_probe_text("Default Version: 2") == "Default Version: 2"


def test_clean_probe_text_removes_leading_bom() -> None:
    assert _clean_probe_text(_BOM + "Default Version: 2") == "Default Version: 2"


def test_clean_probe_text_removes_embedded_nul_characters() -> None:
    mangled = "\x00".join("Default Version: 2")
    assert _clean_probe_text(mangled) == "Default Version: 2"


def test_clean_probe_text_preserves_first_real_character_when_no_bom() -> None:
    # Regression guard: an earlier buggy implementation matched an always-true empty-string prefix
    # and unconditionally stripped the first character even when no BOM was present.
    assert _clean_probe_text("Default Version: 2").startswith("Default Version: 2")


def test_docker_version_parse_and_floor() -> None:
    assert parse_docker_version("Docker version 24.0.7, build afdd53b") == (24, 0, 7)
    assert evaluate_docker("Docker version 24.0.7, build x").status is CheckStatus.PASS
    assert evaluate_docker("Docker version 20.10.0, build x").status is CheckStatus.FAIL
    assert evaluate_docker("").status is CheckStatus.UNAVAILABLE


def test_wsl_default_version() -> None:
    assert evaluate_wsl("Default Version: 2").status is CheckStatus.PASS
    assert evaluate_wsl("Default Version: 1").status is CheckStatus.FAIL
    assert evaluate_wsl("").status is CheckStatus.UNAVAILABLE


def test_wsl_default_version_survives_utf16_mangled_output() -> None:
    # wsl.exe writes UTF-16LE; a mismatched decode interleaves NUL bytes into the text and may
    # prepend a BOM. The parser must still recover the real "Default Version: 2" content.
    mangled = _BOM + "\x00".join("Default Version: 2")
    assert evaluate_wsl(mangled).status is CheckStatus.PASS
    mangled_fail = "\x00".join("Default Version: 1")
    assert evaluate_wsl(mangled_fail).status is CheckStatus.FAIL


def test_nvidia_parse_and_floor() -> None:
    header = "Driver Version: 550.54.14   CUDA Version: 12.4"
    assert parse_nvidia_smi(header) == ((12, 4), "550.54.14")
    assert evaluate_nvidia(header).status is CheckStatus.PASS
    assert evaluate_nvidia("Driver Version: 470.0  CUDA Version: 11.4").status is CheckStatus.FAIL
    assert evaluate_nvidia("no gpu here").status is CheckStatus.UNAVAILABLE


def test_nvidia_recent_cuda_minor_versions_pass() -> None:
    # Version-format drift: recent driver branches report CUDA 12.6/12.8/etc.
    check_a = evaluate_nvidia("Driver Version: 560.35.03  CUDA Version: 12.6")
    check_b = evaluate_nvidia("Driver Version: 570.86.10  CUDA Version: 12.8")
    assert check_a.status is CheckStatus.PASS
    assert check_b.status is CheckStatus.PASS


def test_nvidia_driver_only_install_reports_fail_not_unavailable() -> None:
    # A real, common nvidia-smi output when only the driver (not the CUDA toolkit) is installed.
    header = "Driver Version: 550.54.14      CUDA Version: N/A"
    cuda, driver = parse_nvidia_smi(header)
    assert cuda is None
    assert driver == "550.54.14"
    check = evaluate_nvidia(header)
    # Must be FAIL (a present-but-non-compliant host), never UNAVAILABLE (which would collapse it
    # into "no NVIDIA hardware at all" and lose the driver-version fact).
    assert check.status is CheckStatus.FAIL
    assert dict(check.facts)["driver_version"] == "550.54.14"


def test_nvidia_no_hardware_at_all_is_unavailable() -> None:
    cuda, driver = parse_nvidia_smi("no gpu here")
    assert cuda is None
    assert driver is None
    assert evaluate_nvidia("no gpu here").status is CheckStatus.UNAVAILABLE


def test_ollama_list_parse() -> None:
    listing = "NAME            ID    SIZE\nqwen3:8b   abc   5GB\nqwen3:14b  def   9GB"
    assert set(parse_ollama_list(listing)) == {"qwen3:8b", "qwen3:14b"}


def test_ollama_models_pass_when_all_approved_present() -> None:
    installed = tuple(sorted(APPROVED_LOCAL_MODELS))
    assert evaluate_ollama_models(installed).status is CheckStatus.PASS


def test_ollama_models_fail_when_missing() -> None:
    check = evaluate_ollama_models(("qwen3:8b",))
    assert check.status is CheckStatus.FAIL
    assert "qwen3:14b" in dict(check.facts)["missing"]


def test_ollama_excluded_model_present_fails() -> None:
    installed = (*sorted(APPROVED_LOCAL_MODELS), "glm-4.7")
    assert evaluate_ollama_models(installed).status is CheckStatus.FAIL


def test_ollama_unavailable_when_empty() -> None:
    assert evaluate_ollama_models(()).status is CheckStatus.UNAVAILABLE
