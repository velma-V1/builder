"""Design token validation: completeness + WCAG contrast floor."""

from __future__ import annotations

import pytest

from factory.ui_studio.design_tokens import (
    contrast_ratio,
    default_token_set,
    relative_luminance,
    validate_token_set,
)
from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import DesignTokenSet


def test_default_token_set_is_valid() -> None:
    validate_token_set(default_token_set())  # must not raise


def test_black_on_white_has_maximum_contrast() -> None:
    ratio = contrast_ratio("#000000", "#ffffff")
    assert ratio == pytest.approx(21.0, rel=1e-3)


def test_same_color_has_minimum_contrast() -> None:
    assert contrast_ratio("#808080", "#808080") == pytest.approx(1.0)


def test_relative_luminance_of_white_is_one() -> None:
    assert relative_luminance("#ffffff") == pytest.approx(1.0)


def test_relative_luminance_of_black_is_zero() -> None:
    assert relative_luminance("#000000") == pytest.approx(0.0)


def test_incomplete_token_set_is_denied() -> None:
    tokens = DesignTokenSet(colors={"background": "#ffffff"})
    with pytest.raises(UIStudioError) as excinfo:
        validate_token_set(tokens)
    assert excinfo.value.code is UIStudioErrorCode.TOKEN_SET_INCOMPLETE


def test_low_contrast_pairing_is_denied() -> None:
    base = default_token_set()
    tokens = DesignTokenSet(
        colors={**base.colors, "foreground": "#fefefe"},  # near-white on white background
        spacing=base.spacing, typography=base.typography, radii=base.radii, motion=base.motion,
    )
    with pytest.raises(UIStudioError) as excinfo:
        validate_token_set(tokens)
    assert excinfo.value.code is UIStudioErrorCode.TOKEN_CONTRAST_FLOOR_VIOLATION
