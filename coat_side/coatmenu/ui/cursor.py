"""
CoatMenu - the mouse pointer we draw ourselves.

3DCoat hides the system cursor in brush/pen modes, which leaves any panel we show
with no visible pointer at all. Windows can tell us whether the pointer is
actually being drawn (``GetCursorInfo`` → ``CURSOR_SHOWING``), so we draw our own
arrow in exactly that case and nothing otherwise - a visible pointer never gets a
second arrow drawn on top of it.

Shared by the overlay and the editor; both pass a widget-local position.
"""
from __future__ import annotations

import ctypes
import os

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

CURSOR_SHOWING = 0x00000001


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("hCursor", ctypes.c_void_p),
        ("ptScreenPos", _POINT),
    ]


def _user32():
    try:
        return ctypes.windll.user32
    except Exception:
        return None


def system_cursor_visible() -> bool:
    """True when Windows is drawing the mouse pointer.

    ``COATMENU_FORCE_CURSOR`` overrides the detection (previews and tests: with
    the offscreen Qt platform there is no real cursor state to read).
    """
    force = os.environ.get("COATMENU_FORCE_CURSOR")
    if force:
        return force.strip().lower() not in ("0", "false", "off", "no")
    u = _user32()
    if u is None:
        return True
    try:
        info = _CURSORINFO()
        info.cbSize = ctypes.sizeof(_CURSORINFO)
        if not u.GetCursorInfo(ctypes.byref(info)):
            return True
        return bool(info.flags & CURSOR_SHOWING)
    except Exception:
        return True


def should_draw(position: QPoint | None) -> bool:
    """Whether our own pointer belongs on screen right now."""
    return position is not None and not system_cursor_visible()


def draw(painter: QPainter, position: QPoint | None) -> None:
    """Draw the classic arrow, hot spot at its tip (position = widget coords)."""
    if not should_draw(position):
        return
    x, y = float(position.x()), float(position.y())
    arrow = QPainterPath()
    arrow.moveTo(x, y)
    arrow.lineTo(x, y + 17.0)
    arrow.lineTo(x + 4.3, y + 12.7)
    arrow.lineTo(x + 7.4, y + 18.8)
    arrow.lineTo(x + 10.3, y + 17.3)
    arrow.lineTo(x + 7.2, y + 11.4)
    arrow.lineTo(x + 12.8, y + 11.0)
    arrow.closeSubpath()
    painter.setPen(QPen(QColor(18, 18, 18, 235), 1.4))
    painter.setBrush(QColor(252, 252, 252, 250))
    painter.drawPath(arrow)


def local_position(widget, screen_position: QPoint | None = None) -> QPoint | None:
    """Cursor position inside *widget*, or None when the cursor is outside it."""
    try:
        from PySide6.QtGui import QCursor
        screen_position = screen_position or QCursor.pos()
        local = widget.mapFromGlobal(screen_position)
        return local if widget.rect().contains(local) else None
    except Exception:
        return None
