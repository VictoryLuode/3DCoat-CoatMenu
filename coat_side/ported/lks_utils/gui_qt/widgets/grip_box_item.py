"""GripBox - Widget wrapper with drag handle for reordering.

Wraps any widget with a thin grip column on the left for drag-drop reordering.
"""
from __future__ import annotations

from typing import Any

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class QGripBoxItem(QFrame):
    """Widget wrapper with drag handle for reordering.

    Wraps a content widget with a thin grip column on the left side.
    The grip column can be dragged to reorder items in a QGripBoxContainer.

    Args:
        content_widget: The widget to wrap
        item_id: Optional identifier for this item
        parent: Parent widget
    """

    def __init__(
        self,
        content_widget: QWidget,
        item_id: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize grip box item.

        Args:
            content_widget: Widget to wrap
            item_id: Optional identifier
            parent: Parent widget
        """
        super().__init__(parent)

        self.content_widget = content_widget
        self.item_id = item_id
        self._drag_start_pos: QPoint | None = None

        # Frame styling
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QGripBoxItem {
                background-color: transparent;
                margin: 0px;
                padding: 0px;
            }
            QGripBoxItem:hover {
                background-color: #313131;
            }
        """)

        # Set size policy to prevent vertical expansion
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Layout: [grip column] [content]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Grip column - fixed width
        self._grip_column = QFrame()
        self._grip_column.setFixedWidth(14)
        self._grip_column.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-right: 1px solid #1a1a1a;
            }
            QFrame:hover {
                background-color: #2f2f2f;
            }
        """)
        self._grip_column.setCursor(Qt.SizeVerCursor)

        # Grip icon (centered vertically)
        grip_layout = QVBoxLayout(self._grip_column)
        grip_layout.setContentsMargins(0, 0, 0, 0)
        grip_layout.addStretch()

        grip_icon = QLabel("⋮⋮")
        grip_icon.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 11px;
                padding: 0px;
                background-color: transparent;
            }
        """)
        grip_icon.setAlignment(Qt.AlignCenter)
        grip_icon.setToolTip("Drag to reorder")
        grip_layout.addWidget(grip_icon)

        grip_layout.addStretch()

        layout.addWidget(self._grip_column)

        # Content widget
        layout.addWidget(content_widget, 1)

    def mousePressEvent(self, event: Any) -> None:
        """Start drag on grip column click."""
        if event.button() == Qt.LeftButton:
            # Check if click is on grip column
            if self._grip_column.geometry().contains(event.pos()):
                self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Initiate drag if moved far enough."""
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self._drag_start_pos:
            return

        # Check if moved far enough to start drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"grip_box_{id(self)}")
        drag.setMimeData(mime_data)

        # Execute drag
        drag.exec(Qt.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event: Any) -> None:
        """Clear drag state."""
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)
