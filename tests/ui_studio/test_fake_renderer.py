"""Deterministic fake renderer: success, scripted failure, scripted timeout. No build tool runs."""

from __future__ import annotations

import pytest
from us_support import render_request, renderer

from factory.ui_studio.fake_renderer import RenderFailure, RenderTimeout
from factory.ui_studio.models import BuildStatus


def test_render_produces_source_files_and_tests_across_all_four_test_tools() -> None:
    result = renderer().render(render_request("builder-command-center"))
    assert result.build_status is BuildStatus.DRY_RUN_OK
    assert result.source_files
    kinds = {t.kind for t in result.tests}
    assert kinds == {"vitest", "testing-library", "playwright", "axe-core"}


def test_render_is_deterministic_across_calls() -> None:
    request = render_request("analytics-dashboard")
    first = renderer().render(request)
    second = renderer().render(request)
    assert first.source_files == second.source_files
    assert first.tests == second.tests


def test_scripted_render_failure_raises() -> None:
    fake = renderer(fail_template_ids=frozenset({"builder-command-center"}))
    with pytest.raises(RenderFailure):
        fake.render(render_request("builder-command-center"))


def test_scripted_render_timeout_raises() -> None:
    fake = renderer(timeout_template_ids=frozenset({"builder-command-center"}))
    with pytest.raises(RenderTimeout):
        fake.render(render_request("builder-command-center"))


def test_a_template_with_no_widgets_still_renders_tokens_and_pages() -> None:
    result = renderer().render(render_request("product-landing-page"))
    assert any(f.purpose == "page" for f in result.source_files)
    assert any(f.purpose == "tokens" for f in result.source_files)
