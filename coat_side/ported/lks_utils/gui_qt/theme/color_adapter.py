"""Bidirectional adapter between ported.lks_utils Color and PySide6 QColor."""
from __future__ import annotations

from ported.lks_utils.theme.color import Color

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtGui import QColor


def to_qcolor(color: Color) -> QColor:
    """Convert a :class:`~ported.lks_utils.theme.Color` to a :class:`QColor`."""
    return QColor(color.r, color.g, color.b, color.a)


def from_qcolor(qcolor: QColor) -> Color:
    """Convert a :class:`QColor` to a :class:`~ported.lks_utils.theme.Color`."""
    return Color(
        r=qcolor.red(),
        g=qcolor.green(),
        b=qcolor.blue(),
        a=qcolor.alpha(),
    )


__all__ = ["to_qcolor", "from_qcolor"]
