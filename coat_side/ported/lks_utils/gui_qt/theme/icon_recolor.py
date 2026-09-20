"""SVG icon recolouring helpers.

Provides fast text-substitution recolouring of SVG icons keyed on
palette slot names.  The resulting ``QIcon`` is cached keyed by
``(path, theme_name, fill_slot, stroke_slot)`` and cleared on every
``QThemeProvider.theme_changed`` signal.
"""
from __future__ import annotations

import re
from pathlib import Path

from ported.lks_utils.theme.color import Color
from ported.lks_utils.theme.theme import Theme

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QByteArray


# ---------------------------------------------------------------------------
# Low-level text substitution
# ---------------------------------------------------------------------------

_COLOR_ATTR_RE = re.compile(
    r'((?:fill|stroke|color)\s*=\s*")([^"]*?)(")',
    re.IGNORECASE,
)
_CSS_FILL_RE = re.compile(
    r'(fill\s*:\s*)([^;}"\']+)',
    re.IGNORECASE,
)


def _is_non_paint_value(value: str) -> bool:
    """Return True when a paint token should remain unchanged.

    Keep transparent/non-paint values intact so SVG geometry that is meant to
    be hollow (for example ``fill=\"none\"``) does not get filled during
    recoloring.
    """
    token = value.strip().lower()
    if token in {"", "none", "transparent"}:
        return True
    if token.startswith("url("):
        return True
    return False


def recolor_svg(
    svg_text: str,
    *,
    fill: Color | str | None = None,
    stroke: Color | str | None = None,
) -> str:
    """Return *svg_text* with all ``fill``/``stroke`` attributes replaced.

    Accepts either a :class:`~ported.lks_utils.theme.Color` or a plain hex string.
    Pass ``None`` to leave that attribute unchanged.
    """

    def _hex(value: Color | str) -> str:
        if isinstance(value, str):
            raw = value.lstrip("#")
            if len(raw) == 8:
                return raw[:6]
            return raw
        # SVG color attributes are more reliably supported as #RRGGBB than
        # #RRGGBBAA across Qt SVG backends.
        return f"{value.r:02x}{value.g:02x}{value.b:02x}"

    def _replace(m: re.Match) -> str:
        attr_name = m.group(1).lower().split("=")[0].strip()
        attr_value = m.group(2).strip()
        if fill is not None and attr_name in ("fill", "color"):
            if _is_non_paint_value(attr_value):
                return m.group(0)
            return m.group(1) + "#" + _hex(fill) + m.group(3)
        if stroke is not None and attr_name == "stroke":
            if _is_non_paint_value(attr_value):
                return m.group(0)
            return m.group(1) + "#" + _hex(stroke) + m.group(3)
        return m.group(0)

    result = _COLOR_ATTR_RE.sub(_replace, svg_text)

    # Also patch inline CSS fill: inside style="..."
    if fill is not None:
        result = _CSS_FILL_RE.sub(
            lambda m: m.group(0)
            if _is_non_paint_value(m.group(2))
            else m.group(1) + "#" + _hex(fill),
            result,
        )
    return result


# ---------------------------------------------------------------------------
# High-level: palette-slot-keyed, cached QIcon
# ---------------------------------------------------------------------------

# Cache: (path_str, theme_name, fill_slot, stroke_slot) -> QIcon
_icon_cache: dict[tuple[str, str, str, str | None], QIcon] = {}


def _clear_cache(_theme: object = None) -> None:
    _icon_cache.clear()


def _ensure_connected() -> None:
    """Connect cache-clear to the provider's signal (lazy, once)."""
    global _connected
    if _connected:
        return
    from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider
    QThemeProvider.instance().theme_changed.connect(_clear_cache)
    _connected = True


_connected = False


def recolor_svg_to_palette(
    svg_path: Path,
    *,
    fill_slot: str,
    stroke_slot: str | None = None,
    theme: Theme | None = None,
) -> QIcon:
    """Return a ``QIcon`` with *svg_path*'s colours swapped from a palette.

    Parameters
    ----------
    svg_path:
        Path to the source ``.svg`` file.
    fill_slot:
        Name of the ``Palette`` slot to use as the fill colour
        (e.g. ``"text_primary"``).
    stroke_slot:
        Optional ``Palette`` slot for the stroke colour.
    theme:
        Theme to read from.  Defaults to the current
        ``QThemeProvider`` theme.
    """
    _ensure_connected()

    if theme is None:
        from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider
        theme = QThemeProvider.instance().current()

    key = (str(svg_path), theme.name, fill_slot, stroke_slot)
    if key in _icon_cache:
        return _icon_cache[key]

    fill_color: Color = getattr(theme.palette, fill_slot)
    stroke_color: Color | None = (
        getattr(theme.palette, stroke_slot) if stroke_slot else None
    )

    svg_text = svg_path.read_text(encoding="utf-8")
    recolored = recolor_svg(
        svg_text,
        fill=fill_color,
        stroke=stroke_color,
    )

    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(recolored.encode("utf-8")), "SVG")
    icon = QIcon(pixmap)
    _icon_cache[key] = icon
    return icon


__all__ = ["recolor_svg", "recolor_svg_to_palette"]
