"""Stage-3 unit — host readiness parsers and compatibility evaluators."""

from __future__ import annotations

from factory.livegate.models import CheckStatus
from factory.livegate.version_probe import (
    APPROVED_LOCAL_MODELS,
    evaluate_docker,
    evaluate_nvidia,
    evaluate_ollama_models,
    evaluate_wsl,
    parse_docker_version,
    parse_nvidia_smi,
    parse_ollama_list,
)


def test_docker_version_parse_and_floor() -> None:
    assert parse_docker_version("Docker version 24.0.7, build afdd53b") == (24, 0, 7)
    assert evaluate_docker("Docker version 24.0.7, build x").status is CheckStatus.PASS
    assert evaluate_docker("Docker version 20.10.0, build x").status is CheckStatus.FAIL
    assert evaluate_docker("").status is CheckStatus.UNAVAILABLE


def test_wsl_default_version() -> None:
    assert evaluate_wsl("Default Version: 2").status is CheckStatus.PASS
    assert evaluate_wsl("Default Version: 1").status is CheckStatus.FAIL
    assert evaluate_wsl("").status is CheckStatus.UNAVAILABLE


def test_nvidia_parse_and_floor() -> None:
    header = "Driver Version: 550.54.14   CUDA Version: 12.4"
    assert parse_nvidia_smi(header) == ((12, 4), "550.54.14")
    assert evaluate_nvidia(header).status is CheckStatus.PASS
    assert evaluate_nvidia("Driver Version: 470.0  CUDA Version: 11.4").status is CheckStatus.FAIL
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
