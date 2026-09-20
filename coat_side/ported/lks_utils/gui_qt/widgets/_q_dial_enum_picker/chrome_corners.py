"""Rounded-corner path helpers for QDialEnumPicker chrome."""

from __future__ import annotations

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QPainterPath


def inner_chrome_radius(outer_radius_px: int, inset_px: int) -> int:
    """Corner radius for children inset *inset_px* inside a rounded outer frame."""
    return max(0, outer_radius_px - inset_px)


def left_rounded_rect_path(rect: QRect, radius_px: int) -> QPainterPath:
    """Build a path filling *rect* with only the left edge corners rounded."""
    path = QPainterPath()
    if radius_px <= 0:
        path.addRect(QRectF(rect))
        return path

    radius = float(radius_px)
    box = QRectF(rect)
    path.moveTo(box.left() + radius, box.top())
    path.lineTo(box.right(), box.top())
    path.lineTo(box.right(), box.bottom())
    path.lineTo(box.left() + radius, box.bottom())
    path.arcTo(
        box.left(),
        box.bottom() - (2.0 * radius),
        2.0 * radius,
        2.0 * radius,
        180.0,
        90.0,
    )
    path.lineTo(box.left(), box.top() + radius)
    path.arcTo(box.left(), box.top(), 2.0 * radius, 2.0 * radius, 180.0, -90.0)
    path.closeSubpath()
    return path


def rounded_rect_path(rect: QRect, radius_px: int) -> QPainterPath:
    """Build a path filling *rect* with all corners rounded."""
    path = QPainterPath()
    if radius_px <= 0:
        path.addRect(QRectF(rect))
        return path
    path.addRoundedRect(QRectF(rect), float(radius_px), float(radius_px))
    return path
