"""Gray chrome tokens for QDialEnumPicker derived from Theme palette."""
from __future__ import annotations

from dataclasses import dataclass

from ported.lks_utils.theme.color import Color
from ported.lks_utils.theme.theme import Theme


def _qss_hex(color: Color) -> str:
    """Return ``#RRGGBB`` for Qt QSS / QColor.

    Theme ``Color.to_hex()`` emits ``#RRGGBBAA``, but Qt interprets 8-digit
    hex as ``#AARRGGBB`` — the alpha bytes land in the blue channel and tint
    chrome navy. Always strip alpha for widget stylesheets.
    """
    return f"#{color.to_hex()[1:7]}"


@dataclass(frozen=True)
class DialEnumPickerColors:
    """Resolved gray-scale chrome for the dial enum picker."""

    frame_bg: str
    value_bg: str
    value_hover: str
    border: str
    text: str
    popup_bg: str
    popup_hover: str
    popup_selected: str
    scrollbar_track: str
    scrollbar_handle: str


def resolve_dial_enum_picker_colors(theme: Theme) -> DialEnumPickerColors:
    """Map semantic palette slots to dial-picker gray chrome."""
    palette = theme.palette
    return DialEnumPickerColors(
        frame_bg=_qss_hex(palette.panel_bg_alt),
        value_bg=_qss_hex(palette.canvas_bg),
        value_hover=_qss_hex(palette.panel_bg),
        border=_qss_hex(palette.border_strong),
        text=_qss_hex(palette.text_primary),
        popup_bg=_qss_hex(palette.panel_bg_alt),
        popup_hover=_qss_hex(palette.item_fill),
        popup_selected=_qss_hex(palette.grid_major),
        scrollbar_track=_qss_hex(palette.canvas_bg),
        scrollbar_handle=_qss_hex(palette.handle),
    )


__all__ = ["DialEnumPickerColors", "resolve_dial_enum_picker_colors"]
