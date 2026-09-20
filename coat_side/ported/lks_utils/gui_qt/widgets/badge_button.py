"""Badge Button — compact QPushButton with an icon badge aligned left of text.

A QPushButton subclass that displays an icon on the left and text on the
right with a small gap. Styling is self-contained; no external stylesheet
required.

Example::

    from ported.lks_utils.gui_qt.widgets.badge_button import QBadgeButton

    btn = QBadgeButton(QIcon("path/to/icon.svg"), "Invert", tooltip="Invert all")
    btn.clicked.connect(on_invert)
    layout.addWidget(btn)
"""

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

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget

# ── Visual constants ──────────────────────────────────────────────────────────
_ICON_SIZE: int = 16
_H_PAD: int = 8
_V_PAD: int = 3
_MIN_WIDTH: int = 40
_TEXT_SPACE: int = 5  # pixels between icon and text

_STYLE: str = (
    "QPushButton {"
    f"  padding: {_V_PAD}px {_H_PAD}px;"
    f"  text-align: left;"
    f"  min-width: {_MIN_WIDTH}px;"
    "  border: 1px solid #555;"
    "  border-radius: 3px;"
    "  background-color: #3a3a3a;"
    "  color: #d0d0d0;"
    "  font-size: 12px;"
    "}"
    "QPushButton:hover {"
    "  background-color: #454545;"
    "  border-color: #777;"
    "}"
    "QPushButton:pressed {"
    "  background-color: #2e2e2e;"
    "}"
    "QPushButton:disabled {"
    "  color: #666;"
    "  border-color: #444;"
    "  background-color: #333;"
    "}"
)


class QBadgeButton(QPushButton):
    """Compact button with a left-aligned icon badge and text.

    Args:
        icon: QIcon to display left of the text
        text: Button label text
        tooltip: Optional tooltip text
        icon_size: Size of the icon in pixels (default 16)
        parent: Parent widget
    """

    def __init__(
        self,
        icon: QIcon,
        text: str = "",
        tooltip: str = "",
        icon_size: int = _ICON_SIZE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)

        self.setIcon(icon)
        self.setIconSize(QSize(icon_size, icon_size))
        self.setStyleSheet(_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if tooltip:
            self.setToolTip(tooltip)


__all__ = ["QBadgeButton"]
