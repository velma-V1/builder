"""Design tokens: a validated, deterministic token set. No token set ships without a contrast check.

Colors are validated against a WCAG 2.x relative-luminance contrast floor for the declared
foreground/background pairing — computed here directly (no external color library), so the check
runs fully offline and deterministically.
"""

from __future__ import annotations

from factory.ui_studio.errors import UIStudioError, UIStudioErrorCode
from factory.ui_studio.models import DesignTokenSet

#: WCAG AA floor for normal body text.
MIN_CONTRAST_RATIO = 4.5

_REQUIRED_COLOR_KEYS = frozenset(
    {"background", "foreground", "primary", "primary-foreground", "border", "muted"}
)
_REQUIRED_SPACING_KEYS = frozenset({"xs", "sm", "md", "lg", "xl"})
_REQUIRED_TYPOGRAPHY_KEYS = frozenset({"font-sans", "font-mono", "text-base", "text-lg"})
_REQUIRED_RADII_KEYS = frozenset({"sm", "md", "lg"})
_REQUIRED_MOTION_KEYS = frozenset({"duration-fast", "duration-normal", "easing-standard"})


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    stripped = value.lstrip("#")
    if len(stripped) == 3:
        stripped = "".join(ch * 2 for ch in stripped)
    if len(stripped) != 6:
        raise UIStudioError(
            UIStudioErrorCode.TOKEN_SET_INCOMPLETE, f"not a valid hex color: {value!r}"
        )
    return (int(stripped[0:2], 16), int(stripped[2:4], 16), int(stripped[4:6], 16))


def _channel_luminance(channel_8bit: int) -> float:
    c = channel_8bit / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (
        0.2126 * _channel_luminance(r)
        + 0.7152 * _channel_luminance(g)
        + 0.0722 * _channel_luminance(b)
    )


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    lum_a = relative_luminance(hex_a) + 0.05
    lum_b = relative_luminance(hex_b) + 0.05
    return max(lum_a, lum_b) / min(lum_a, lum_b)


def default_token_set() -> DesignTokenSet:
    return DesignTokenSet(
        colors={
            "background": "#ffffff", "foreground": "#0a0a0a", "primary": "#1d4ed8",
            "primary-foreground": "#ffffff", "border": "#e5e7eb", "muted": "#6b7280",
        },
        spacing={"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "xl": "2rem"},
        typography={
            "font-sans": "Inter, system-ui, sans-serif", "font-mono": "JetBrains Mono, monospace",
            "text-base": "1rem", "text-lg": "1.125rem",
        },
        radii={"sm": "0.25rem", "md": "0.5rem", "lg": "0.75rem"},
        motion={
            "duration-fast": "120ms", "duration-normal": "200ms",
            "easing-standard": "cubic-bezier(0.4,0,0.2,1)",
        },
    )


def validate_token_set(
    tokens: DesignTokenSet, *, min_contrast: float = MIN_CONTRAST_RATIO
) -> None:
    """Raise on an incomplete token set or a fg/bg pairing below the contrast floor."""
    missing_colors = _REQUIRED_COLOR_KEYS - tokens.colors.keys()
    missing_spacing = _REQUIRED_SPACING_KEYS - tokens.spacing.keys()
    missing_typography = _REQUIRED_TYPOGRAPHY_KEYS - tokens.typography.keys()
    missing_radii = _REQUIRED_RADII_KEYS - tokens.radii.keys()
    missing_motion = _REQUIRED_MOTION_KEYS - tokens.motion.keys()
    missing = missing_colors | missing_spacing | missing_typography | missing_radii | missing_motion
    if missing:
        raise UIStudioError(
            UIStudioErrorCode.TOKEN_SET_INCOMPLETE,
            f"missing required token keys: {sorted(missing)}",
        )
    pairs = (
        ("background", "foreground"),
        ("primary", "primary-foreground"),
    )
    for bg_key, fg_key in pairs:
        ratio = contrast_ratio(tokens.colors[bg_key], tokens.colors[fg_key])
        if ratio < min_contrast:
            raise UIStudioError(
                UIStudioErrorCode.TOKEN_CONTRAST_FLOOR_VIOLATION,
                f"{bg_key}/{fg_key} contrast ratio {ratio:.2f} is below the {min_contrast} floor",
            )
