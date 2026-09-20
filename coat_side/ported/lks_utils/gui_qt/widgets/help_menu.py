"""
QHelpMenu — Collapsible help section with scrollable content.

Provides a consistent help/info section with:
- Question mark circle emoji (❓) for visual recognition
- Always collapsed by default
- Scrollable text area with max height
- Built on top of QCollapsibleSection

Usage:
    from ported.lks_utils.gui_qt.widgets import QHelpMenu

    help_menu = QHelpMenu(
        title="About Hotkeys",
        content=(
            "<b>How to use:</b><br/>"
            "Step 1: Do this<br/>"
            "Step 2: Do that<br/>"
        ),
        max_height=200  # Optional, default 200
    )
    layout.addWidget(help_menu)
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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ported.lks_utils.gui_qt.widgets.collapsible_section import QCollapsibleSection


class QHelpMenu(QWidget):
    """
    Collapsible help section with scrollable text content.

    Always collapsed by default, uses question mark emoji for consistency.
    """

    def __init__(
        self,
        title: str = "Help",
        content: str = "",
        max_height: int = 200,
        parent: QWidget | None = None,
    ) -> None:
        """
        Create a help menu widget.

        Args:
            title: Title text (without emoji prefix)
            content: HTML or plain text content
            max_height: Maximum height of scroll area in pixels
            parent: Parent widget
        """
        super().__init__(parent)

        # Add question mark emoji prefix
        full_title = f"❓ {title}"

        # Create collapsible section (always collapsed)
        self._section = QCollapsibleSection(
            title=full_title,
            initially_expanded=False,
        )

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(max_height)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            """
        )

        # Create content label
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setStyleSheet("color: #aaa; font-size: 10px; padding: 8px;")
        content_label.setOpenExternalLinks(True)

        scroll_area.setWidget(content_label)
        self._section.content_layout.addWidget(scroll_area)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._section)


__all__ = ["QHelpMenu"]
