"""Themed SVG icon loading for square button presets."""
from __future__ import annotations

from pathlib import Path

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

from ported.lks_utils.gui_qt.theme.icon_recolor import recolor_svg, recolor_svg_to_palette
from ported.lks_utils.theme.color import Color
from ported.lks_utils.theme.theme import Theme

_ICON_DIR = Path(__file__).resolve().parent / "data" / "icons"
_ICON_CACHE: dict[tuple[str, str, str | None], QIcon] = {}


def icon_asset_path(name: str) -> Path:
    """Return the on-disk path for a preset icon asset."""
    stem = name.removesuffix(".svg")
    return _ICON_DIR / f"{stem}.svg"


def preset_icon(
    name: str,
    *,
    palette_slot: str = "text_primary",
    stroke_palette_slot: str | None = None,
    theme: Theme | None = None,
    hex_color: str | None = None,
) -> QIcon:
    """Load a preset SVG icon with theme-token recoloring.

  When *hex_color* is set it overrides palette slots (legacy knowledge tint).
    """
    svg_path = icon_asset_path(name)
    if hex_color is not None:
        cache_key = (name, "hex", hex_color)
        cached = _ICON_CACHE.get(cache_key)
        if cached is not None:
            return cached
        svg_text = svg_path.read_text(encoding="utf-8")
        recolored = recolor_svg(svg_text, fill=hex_color, stroke=hex_color)
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(recolored.encode("utf-8")), "SVG")
        icon = QIcon(pixmap)
        _ICON_CACHE[cache_key] = icon
        return icon

    cache_key = (name, palette_slot, stroke_palette_slot)
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached
    icon = recolor_svg_to_palette(
        svg_path,
        fill_slot=palette_slot,
        stroke_slot=stroke_palette_slot or palette_slot,
        theme=theme,
    )
    _ICON_CACHE[cache_key] = icon
    return icon


def preset_icon_color(
    name: str,
    *,
    color: Color | str,
) -> QIcon:
    """Load a preset icon recolored to an explicit color value."""
    hex_value = color if isinstance(color, str) else color.to_hex()[:7]
    return preset_icon(name, hex_color=hex_value)


__all__ = ["icon_asset_path", "preset_icon", "preset_icon_color"]
