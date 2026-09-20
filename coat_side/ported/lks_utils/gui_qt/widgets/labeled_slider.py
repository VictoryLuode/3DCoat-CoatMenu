"""LabeledSlider widget - A horizontal slider with label and current value display.

Provides a simple way to create sliders with integrated labels and value displays.
"""
from __future__ import annotations

import sys

# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode).
# ctypes only — do not hard-import pythoncom (pywin32); unavailable in 3DCoat Python.
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ported.lks_utils.gui_qt.widgets._modifier_slider import _ModifierSlider

# Default slider styling for dark theme
DEFAULT_SLIDER_STYLE: str = """
    QSlider::groove:horizontal {
        background: #3a3a3a;
        height: 6px;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #90caf9;
        width: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QSlider::handle:horizontal:hover {
        background: #64b5f6;
    }
"""


class QLabeledSlider(QWidget):
    """A horizontal slider with label and current value display.

    Modifier keys during slider drag:

    * **Ctrl**       — snap to 1/32 evenly-spaced grid positions.
    * **Shift**      — fine mode: slider moves at 1/10 normal sensitivity.
    * **Ctrl+Shift** — fine movement constrained to snap grid points.

    Signals:
        value_changed(int): Emitted when slider value changes

    Args:
        parent: Parent widget
        label: Label text
        min_value: Minimum value
        max_value: Maximum value
        initial: Initial value
        suffix: Suffix for value display (e.g., "%")
        label_width: Minimum width of the label
        value_width: Minimum width of the value display

    Example:
        slider = QLabeledSlider(
            parent,
            label="Opacity:",
            min_value=0,
            max_value=100,
            initial=75,
            suffix="%"
        )
        slider.value_changed.connect(self._on_opacity_changed)
    """

    value_changed = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        label: str = "Value:",
        min_value: int = 0,
        max_value: int = 100,
        initial: int = 50,
        suffix: str = "",
        label_width: int = 70,
        value_width: int = 40,
    ) -> None:
        """Initialize labeled slider.

        Args:
            parent: Parent widget
            label: Label text
            min_value: Minimum value
            max_value: Maximum value
            initial: Initial value
            suffix: Suffix for value display
            label_width: Minimum width of label
            value_width: Minimum width of value display
        """
        super().__init__(parent)
        self._suffix: str = suffix
        self._min_value: int = min_value
        self._max_value: int = max_value

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self._label = QLabel(label)
        self._label.setMinimumWidth(label_width)
        layout.addWidget(self._label)

        # Slider
        self._slider = _ModifierSlider(Qt.Horizontal)
        self._slider.setMinimum(min_value)
        self._slider.setMaximum(max_value)
        self._slider.setValue(initial)
        self._slider.setStyleSheet(DEFAULT_SLIDER_STYLE)
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider, 1)

        # Value display
        self._value_label = QLabel()
        self._value_label.setMinimumWidth(value_width)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._update_value_display()
        layout.addWidget(self._value_label)

    def value(self) -> int:
        """Get current value."""
        return self._slider.value()

    def set_value(self, value: int) -> None:
        """Set current value."""
        self._slider.setValue(value)

    def set_range(self, min_value: int, max_value: int) -> None:
        """Set the slider range."""
        self._min_value = min_value
        self._max_value = max_value
        self._slider.setMinimum(min_value)
        self._slider.setMaximum(max_value)

    def set_suffix(self, suffix: str) -> None:
        """Set the value suffix."""
        self._suffix = suffix
        self._update_value_display()

    def set_label(self, label: str) -> None:
        """Set the label text."""
        self._label.setText(label)

    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        self._update_value_display()
        self.value_changed.emit(value)

    def _update_value_display(self) -> None:
        """Update value label display."""
        value = self._slider.value()
        self._value_label.setText(f"{value}{self._suffix}")
