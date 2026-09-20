"""ButtonGrid widget - A grid layout of buttons with consistent styling.

Useful for scope-based operations (Current, Subtree, All) or any
grouped button actions.
"""
from __future__ import annotations

from typing import Callable

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

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

# Default button style for dark theme
DEFAULT_BUTTON_STYLE: str = """
    QPushButton {
        background: #3a3a3a;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 4px 8px;
        color: #ddd;
        min-height: 20px;
    }
    QPushButton:hover { background: #4a4a4a; border-color: #666; }
    QPushButton:pressed { background: #2a2a2a; }
"""


class QButtonGrid(QWidget):
    """A grid of buttons with consistent styling.

    Useful for scope-based operations (Current, Subtree, All).

    Args:
        parent: Parent widget
        columns: Number of columns in the grid
        button_style: CSS style for buttons

    Example:
        grid = QButtonGrid(parent, columns=3)
        grid.add_button("Current", self._on_current)
        grid.add_button("Subtree", self._on_subtree)
        grid.add_button("All", self._on_all)
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        columns: int = 3,
        button_style: str | None = None,
    ) -> None:
        """Initialize button grid.

        Args:
            parent: Parent widget
            columns: Number of columns in grid
            button_style: CSS style override
        """
        super().__init__(parent)
        self._columns: int = columns
        self._button_style: str = button_style or DEFAULT_BUTTON_STYLE
        self._row: int = 0
        self._col: int = 0
        self._buttons: list[QPushButton] = []

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

    def add_button(
        self,
        text: str,
        callback: Callable[[], None],
        tooltip: str | None = None,
        style: str | None = None,
        icon: QIcon | None = None,
        icon_size: int = 16,
    ) -> QPushButton:
        """Add a button to the grid.

        Args:
            text: Button label
            callback: Click handler
            tooltip: Optional tooltip text
            style: Button style override
            icon: Optional QIcon to display left of text
            icon_size: Icon size in pixels (default 16)

        Returns:
            The created button
        """
        btn = QPushButton(text)
        btn.setStyleSheet(style or self._button_style)
        btn.clicked.connect(callback)
        if tooltip:
            btn.setToolTip(tooltip)
        if icon is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(icon_size, icon_size))

        self._layout.addWidget(btn, self._row, self._col)
        self._buttons.append(btn)

        # Advance position
        self._col += 1
        if self._col >= self._columns:
            self._col = 0
            self._row += 1

        return btn

    def add_widget(self, widget: QWidget, colspan: int = 1) -> None:
        """Add a custom widget to the grid.

        Args:
            widget: Widget to add
            colspan: Number of columns to span
        """
        self._layout.addWidget(widget, self._row, self._col, 1, colspan)
        self._col += colspan
        if self._col >= self._columns:
            self._col = 0
            self._row += 1

    def new_row(self) -> None:
        """Move to a new row."""
        if self._col > 0:
            self._row += 1
            self._col = 0

    def get_buttons(self) -> list[QPushButton]:
        """Get list of all buttons in the grid."""
        return self._buttons.copy()

    def set_button_enabled(self, index: int, enabled: bool) -> None:
        """Enable or disable a button by index.

        Args:
            index: Button index
            enabled: Whether to enable
        """
        if 0 <= index < len(self._buttons):
            self._buttons[index].setEnabled(enabled)

    def clear(self) -> None:
        """Remove all buttons from the grid."""
        for btn in self._buttons:
            btn.deleteLater()
        self._buttons.clear()
        self._row = 0
        self._col = 0
