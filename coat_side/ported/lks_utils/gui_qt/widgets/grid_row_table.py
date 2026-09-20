"""
QGridRowTable — QGridLayout wrapper with automatic column-width normalization.

Wraps QGridLayout in a QWidget container. Provides add_cell and add_labeled_row
APIs, and a finalize() method that normalizes column widths to the widest widget
in each column. This eliminates the need for hardcoded setMinimumWidth calls.

Usage:
    from ported.lks_utils.gui_qt.widgets.grid_row_table import QGridRowTable, Align

    table = QGridRowTable()
    table.add_labeled_row(0, "Label:", [btn1, btn2])
    table.add_cell(1, 0, QLabel("Another:"), align=Align.LEFT)
    table.add_cell(1, 1, some_widget)
    table.set_column_stretch(0, 1)
    table.finalize()
    layout.addWidget(table)
"""
from __future__ import annotations

from enum import Enum, auto

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QWidget


# =============================================================================
# Align Enum
# =============================================================================


class Align(str, Enum):
    """Alignment constants for cell widgets placed in the grid."""

    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


_ALIGN_MAP: dict[Align, Qt.AlignmentFlag] = {
    Align.LEFT: Qt.AlignmentFlag.AlignLeft,
    Align.CENTER: Qt.AlignmentFlag.AlignCenter,
    Align.RIGHT: Qt.AlignmentFlag.AlignRight,
}


# =============================================================================
# QGridRowTable
# =============================================================================


class QGridRowTable(QWidget):
    """
    QGridLayout wrapper with automatic column-width normalization.

    Provides add_cell and add_labeled_row APIs. Call finalize() after
    all cells are added to normalize column widths to the widest widget
    in each column. Columns are homogeneous — all widgets in the same
    column share the same minimum width.

    Features:
    - Per-cell alignment via Align enum (LEFT, CENTER, RIGHT)
    - Column stretch via set_column_stretch(col, factor)
    - Spanning cells via colspan parameter
    - Zero margins, 4px spacing by default
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._grid: QGridLayout = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(4)
        self._stretched_columns: set[int] = set()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def add_cell(
        self,
        row: int,
        col: int,
        widget: QWidget,
        align: Align = Align.LEFT,
        colspan: int = 1,
    ) -> None:
        """
        Place a widget at the specified grid position with alignment.

        Args:
            row: Grid row index (0-based)
            col: Grid column index (0-based)
            widget: Widget to place
            align: Horizontal alignment within the cell
            colspan: Number of columns to span
        """
        qt_align: Qt.AlignmentFlag = _ALIGN_MAP.get(align, Qt.AlignmentFlag.AlignLeft)
        self._grid.addWidget(widget, row, col, 1, colspan, qt_align)

    def add_labeled_row(
        self,
        row: int,
        text: str,
        widgets: list[QWidget],
        stretches: dict[int, int] | None = None,
    ) -> None:
        """
        Convenience: label in column 0, widget list in columns 1..N.

        Args:
            row: Grid row index
            text: Label text placed in column 0
            widgets: Widgets placed in columns 1, 2, ... N
            stretches: Optional dict mapping column index to stretch factor
        """
        label: QLabel = QLabel(text)
        self.add_cell(row, 0, label, align=Align.LEFT)
        for i, widget in enumerate(widgets):
            col: int = i + 1
            self.add_cell(row, col, widget)

        if stretches:
            for col, factor in stretches.items():
                self.set_column_stretch(col, factor)

    def set_column_stretch(self, col: int, factor: int) -> None:
        """
        Set the stretch factor for a column.

        Columns with higher stretch factors take proportionally more
        of the available space. Use for sliders, spinboxes, or other
        expandable widgets.

        Columns set via this method are tracked so that finalize()
        does NOT reset their stretch to 0.

        Args:
            col: Column index
            factor: Stretch factor (0 = no stretch)
        """
        self._stretched_columns.add(col)
        self._grid.setColumnStretch(col, factor)

    def finalize(self) -> None:
        """
        Normalize column widths to the widest widget in each column.

        Must be called once after all cells are added. Forces a geometry
        update so widgets have valid sizeHint() values, then measures
        each column and sets column minimum widths.

        Widgets that span multiple columns (colspan > 1) are excluded
        from per-column width calculations.
        """
        # Force a geometry pass so widgets report accurate size hints
        self.updateGeometry()
        QApplication.processEvents()

        grid: QGridLayout = self._grid
        col_count: int = grid.columnCount()

        # Collect maximum width per column (colspan=1 only)
        col_widths: dict[int, int] = {}

        for i in range(grid.count()):
            item = grid.itemAt(i)
            if item is None:
                continue
            widget: QWidget | None = item.widget()
            if widget is None:
                continue

            _row: int
            _col: int
            _row_span: int
            _col_span: int
            _row, _col, _row_span, _col_span = grid.getItemPosition(i)

            # Skip spanning widgets — can't decompose their width per-column
            if _col_span > 1:
                continue

            hint_width: int = widget.sizeHint().width()
            current_max: int = col_widths.get(_col, 0)
            if hint_width > current_max:
                col_widths[_col] = hint_width

        # Apply minimum widths
        for col, width in col_widths.items():
            grid.setColumnMinimumWidth(col, width)

        # Reset stretch to 0 for columns NOT explicitly stretched.
        # This prevents QGridLayout from distributing extra space
        # across non-stretch columns (e.g. labels, buttons) when
        # the container is wider than the sum of minimum widths.
        for col in range(col_count):
            if col not in self._stretched_columns:
                grid.setColumnStretch(col, 0)

    # -------------------------------------------------------------------------
    # Layout property accessor
    # -------------------------------------------------------------------------

    @property
    def grid_layout(self) -> QGridLayout:
        """Access the underlying QGridLayout for advanced operations."""
        return self._grid


__all__ = ["QGridRowTable", "Align"]
