"""Single-path chrome painting for QDialEnumPicker."""

from __future__ import annotations

from typing import Literal

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.chrome_corners import rounded_rect_path
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_default_theme import DialEnumPickerColors

StepperHover = Literal["none", "up", "down"]

_BORDER_WIDTH_PX: float = 1.0


def _qcolor(hex_color: str) -> QColor:
    return QColor(hex_color)


def _outer_stroke_rect(widget_rect: QRect) -> QRectF:
    """Pixel-aligned rect for a 1px antialiased stroke along the widget edge."""
    return QRectF(widget_rect).adjusted(
        _BORDER_WIDTH_PX / 2.0,
        _BORDER_WIDTH_PX / 2.0,
        -_BORDER_WIDTH_PX / 2.0,
        -_BORDER_WIDTH_PX / 2.0,
    )


def paint_dial_enum_chrome(
    painter: QPainter,
    widget_rect: QRect,
    *,
    value_rect: QRect,
    stepper_rect: QRect,
    colors: DialEnumPickerColors,
    border_radius_px: int,
    value_hovered: bool,
    stepper_hover: StepperHover,
) -> None:
    """Paint border, fills, and dividers from one authoritative outer contour.

    All interior fills are clipped to the same rounded outer path so stroke and
    fill never drift apart at the corners.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    radius = float(max(0, border_radius_px))
    outer_path = rounded_rect_path(widget_rect, border_radius_px)
    border_pen = QPen(_qcolor(colors.border), _BORDER_WIDTH_PX)

    # --- fills (clipped to outer contour) ---
    painter.setClipPath(outer_path)
    painter.setPen(Qt.PenStyle.NoPen)

    painter.setBrush(_qcolor(colors.frame_bg))
    painter.drawRect(widget_rect)

    value_fill = colors.value_hover if value_hovered else colors.value_bg
    painter.setBrush(_qcolor(value_fill))
    painter.drawRect(value_rect)

    if stepper_hover in ("up", "down"):
        painter.setBrush(_qcolor(colors.value_hover))
        if stepper_hover == "up":
            hover_rect = QRect(
                stepper_rect.left(),
                stepper_rect.top(),
                stepper_rect.width(),
                stepper_rect.height() // 2,
            )
        else:
            hover_rect = QRect(
                stepper_rect.left(),
                stepper_rect.top() + stepper_rect.height() // 2,
                stepper_rect.width(),
                stepper_rect.height() - stepper_rect.height() // 2,
            )
        painter.drawRect(hover_rect)

    # --- dividers (still clipped) ---
    painter.setPen(border_pen)
    painter.drawLine(
        stepper_rect.left(),
        stepper_rect.top(),
        stepper_rect.left(),
        stepper_rect.bottom(),
    )
    stepper_mid_y = stepper_rect.top() + stepper_rect.height() // 2
    painter.drawLine(
        stepper_rect.left(),
        stepper_mid_y,
        stepper_rect.right(),
        stepper_mid_y,
    )

    painter.setClipping(False)

    # --- authoritative outer stroke ---
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(border_pen)
    stroke_rect = _outer_stroke_rect(widget_rect)
    if radius <= 0.0:
        painter.drawRect(stroke_rect)
    else:
        painter.drawRoundedRect(stroke_rect, radius, radius)

    painter.restore()
