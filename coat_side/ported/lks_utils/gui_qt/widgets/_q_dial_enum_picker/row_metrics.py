"""Measure composed dial enum option rows."""
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

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QWidget

from ported.lks_utils.gui_qt.widgets.dial_enum_option import DialEnumOption
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_metrics import (
    ADORNMENT_GAP_PX,
    ADORNMENT_SIZE_PX,
    HORIZONTAL_PADDING_PX,
    STEPPER_WIDTH_PX,
    TEXT_MEASURE_FUDGE_PX,
    VERTICAL_PADDING_PX,
)


def adornment_width(adornment: object | None, *, adornment_px: int) -> int:
    """Return horizontal space used by one adornment slot."""
    if adornment is None:
        return 0
    if isinstance(adornment, QWidget):
        hint = adornment.sizeHint()
        return max(adornment_px, hint.width())
    return adornment_px


def measure_option_row_width(
    option: DialEnumOption,
    metrics: QFontMetrics,
    *,
    adornment_px: int = ADORNMENT_SIZE_PX,
) -> int:
    """Measure one option row at the given font metrics."""
    leading_w = adornment_width(option.leading, adornment_px=adornment_px)
    trailing_w = adornment_width(option.trailing, adornment_px=adornment_px)
    text_w = max(
        metrics.horizontalAdvance(option.label),
        metrics.boundingRect(option.label).width(),
    ) + TEXT_MEASURE_FUDGE_PX
    gaps = 0
    if leading_w:
        gaps += ADORNMENT_GAP_PX
    if trailing_w:
        gaps += ADORNMENT_GAP_PX
    return leading_w + text_w + trailing_w + gaps


def measure_option_row_height(
    option: DialEnumOption,
    metrics: QFontMetrics,
    *,
    adornment_px: int = ADORNMENT_SIZE_PX,
) -> int:
    """Measure row height from text line and adornments."""
    adorn_h = adornment_px if (option.leading or option.trailing) else 0
    return max(metrics.height(), adorn_h)


def shrink_to_largest_size(
    host: QWidget,
    options: list[DialEnumOption],
    *,
    adornment_px: int = ADORNMENT_SIZE_PX,
) -> tuple[int, int]:
    """Return (width, height) for shrink-to-largest mode."""
    metrics = host.fontMetrics()
    if not options:
        return (
            HORIZONTAL_PADDING_PX * 2 + STEPPER_WIDTH_PX + 48,
            VERTICAL_PADDING_PX * 2 + metrics.height(),
        )
    max_row_w = max(
        measure_option_row_width(opt, metrics, adornment_px=adornment_px)
        for opt in options
    )
    max_row_h = max(
        measure_option_row_height(opt, metrics, adornment_px=adornment_px)
        for opt in options
    )
    width = max_row_w + (HORIZONTAL_PADDING_PX * 2) + STEPPER_WIDTH_PX
    height = max_row_h + (VERTICAL_PADDING_PX * 2)
    return width, height
