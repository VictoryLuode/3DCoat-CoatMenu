"""Info buttons with floating help popups.

Provides two variants sharing the same ``QInfoPopup``:
- ``QInfoButton`` — standard square button with accent-blue circular ``?`` icon
- ``QInfoButtonCompact`` — compact circular ``?`` button for inline use
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

import sys
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(
            None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication, QFrame, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

# =============================================================================
# CONSTANTS
# =============================================================================

_STANDARD_SIZE: int = 22
_COMPACT_SIZE: int = 16
_POPUP_MAX_WIDTH: int = 320
_POPUP_MAX_HEIGHT: int = 300
_POPUP_PADDING: int = 12

# 3DCoat accent blue — used across both LKS and ported.lks_utils
_ACCENT_BLUE: str = "#90caf9"


# =============================================================================
# QInfoPopup
# =============================================================================

class QInfoPopup(QFrame):
    """Frameless floating panel that displays help text.

    Uses ``Qt.WindowType.Popup`` so it auto-dismisses when the user
    clicks anywhere outside the popup or presses Escape.
    """

    def __init__(
        self,
        text: str,
        parent: QWidget | None = None,
        max_width: int = _POPUP_MAX_WIDTH,
        max_height: int = _POPUP_MAX_HEIGHT,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setStyleSheet("""
            QInfoPopup {
                background-color: #2d2d2d;
                border: 1px solid #505050;
                border-radius: 6px;
            }
        """)

        layout: QVBoxLayout = QVBoxLayout(self)
        layout.setContentsMargins(_POPUP_PADDING, _POPUP_PADDING,
                                  _POPUP_PADDING, _POPUP_PADDING)
        layout.setSpacing(0)

        scroll: QScrollArea = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(max_height)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        label: QLabel = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet(f"""
            QLabel {{
                color: #ccc;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
                max-width: {max_width - _POPUP_PADDING * 2}px;
            }}
        """)
        label.setOpenExternalLinks(True)

        scroll.setWidget(label)
        layout.addWidget(scroll)

        self.setMaximumWidth(max_width)

    def show_at_button(self, button: QWidget) -> None:
        """Position and show the popup near *button*, staying in screen bounds."""
        self.adjustSize()

        btn_global: QPoint = button.mapToGlobal(QPoint(0, 0))
        btn_w: int = button.width()
        btn_h: int = button.height()

        popup_w: int = self.sizeHint().width()
        popup_h: int = min(self.sizeHint().height(), _POPUP_MAX_HEIGHT)

        x: int = btn_global.x() + btn_w - popup_w
        y: int = btn_global.y() + btn_h + 4

        screen: QRect | None = None
        app = QApplication.instance()
        if app is not None:
            screen_list = app.screens()
            if screen_list:
                screen = screen_list[0].availableGeometry()

        if screen is not None:
            if x + popup_w > screen.right():
                x = screen.right() - popup_w - 4
            if x < screen.left():
                x = screen.left() + 4
            if y + popup_h > screen.bottom():
                y = btn_global.y() - popup_h - 4
                if y < screen.top():
                    y = screen.top() + 4

        self.move(x, y)
        self.show()


# =============================================================================
# QInfoButton (standard — square with backdrop + circular ? icon)
# =============================================================================

class QInfoButton(QPushButton):
    """Standard square info button with a circular ``?`` icon.

    Uses the same square-with-backdrop style as other action buttons.
    The ``?`` is rendered as a circular accent-blue badge centered
    inside the button area.

    Dimensions: 22×22 px (configurable).
    """

    def __init__(
        self,
        help_text: str = "",
        parent: QWidget | None = None,
        size: int = _STANDARD_SIZE,
        popup_max_width: int = _POPUP_MAX_WIDTH,
        popup_max_height: int = _POPUP_MAX_HEIGHT,
    ) -> None:
        super().__init__(parent)
        self._help_text: str = help_text
        self._size: int = size
        self._popup_max_width: int = popup_max_width
        self._popup_max_height: int = popup_max_height
        self._popup: QInfoPopup | None = None

        circle: int = max(size - 4, 10)  # circular badge is slightly inset

        # Use object-name selector so the stylesheet has higher
        # specificity than generic QPushButton rules inherited from
        # parent/application stylesheets (e.g. dark theme overrides).
        self.setObjectName("_lks_info_standard")

        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click for more information")
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Square backdrop button containing a circular ? badge
        self.setStyleSheet(f"""
            QPushButton#_lks_info_standard {{
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 0px;
                min-width: 0px;
                min-height: 0px;
            }}
            QPushButton#_lks_info_standard:hover {{
                background-color: #4a4a4a;
                border-color: #666666;
            }}
            QPushButton#_lks_info_standard:pressed {{
                background-color: #2a2a2a;
            }}
        """)

        self.setText("?")
        self.setStyleSheet(self.styleSheet() + f"""
            QPushButton#_lks_info_standard {{
                color: {_ACCENT_BLUE};
                font-size: {max(8, circle - 6)}px;
                font-weight: bold;
                font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
            }}
            QPushButton#_lks_info_standard:hover {{
                color: #ffffff;
            }}
        """)

        self.clicked.connect(self._toggle_popup)

    def set_help_text(self, text: str) -> None:
        """Update the help text displayed in the popup."""
        self._help_text = text

    def help_text(self) -> str:
        """Return the current help text."""
        return self._help_text

    def _toggle_popup(self) -> None:
        """Show or hide the info popup."""
        if self._popup is not None and self._popup.isVisible():
            self._popup.hide()
            self._popup = None
            return

        if not self._help_text.strip():
            return

        self._popup = QInfoPopup(
            text=self._help_text,
            max_width=self._popup_max_width,
            max_height=self._popup_max_height,
        )
        self._popup.show_at_button(self)

    def hide_popup(self) -> None:
        """Hide the popup if it's visible."""
        if self._popup is not None:
            self._popup.hide()
            self._popup = None


# =============================================================================
# QInfoButtonCompact — small circular ? for inline / header use
# =============================================================================

class QInfoButtonCompact(QPushButton):
    """Compact circular ``?`` button that fits inline in headers.

    Small accent-blue circle (no square backdrop) suitable for placing
    inside collapsible section headers or other tight layouts.

    Dimensions: 16×16 px (configurable).
    """

    def __init__(
        self,
        help_text: str = "",
        parent: QWidget | None = None,
        size: int = _COMPACT_SIZE,
        popup_max_width: int = _POPUP_MAX_WIDTH,
        popup_max_height: int = _POPUP_MAX_HEIGHT,
    ) -> None:
        super().__init__(parent)
        self._help_text: str = help_text
        self._size: int = size
        self._popup_max_width: int = popup_max_width
        self._popup_max_height: int = popup_max_height
        self._popup: QInfoPopup | None = None

        radius: int = size // 2

        # Use object-name selector so the stylesheet has higher
        # specificity than generic QPushButton rules inherited from
        # parent/application stylesheets (e.g. dark theme overrides).
        self.setObjectName("_lks_info_compact")

        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click for more information")
        # NOTE: Do NOT call setFlat(True) — it prevents stylesheet
        # backgrounds from rendering on some Qt/Windows configurations.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setText("?")

        self.setStyleSheet(f"""
            QPushButton#_lks_info_compact {{
                background-color: rgba(144, 202, 249, 0.15);
                color: {_ACCENT_BLUE};
                border: 1px solid {_ACCENT_BLUE};
                border-radius: {radius}px;
                font-size: {max(7, size - 6)}px;
                font-weight: bold;
                font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
                padding: 0px;
                min-width: {size}px;
                max-width: {size}px;
                min-height: {size}px;
                max-height: {size}px;
                width: {size}px;
                height: {size}px;
            }}
            QPushButton#_lks_info_compact:hover {{
                background-color: {_ACCENT_BLUE};
                color: #1a1a1a;
                border-color: {_ACCENT_BLUE};
            }}
            QPushButton#_lks_info_compact:pressed {{
                background-color: #64b5f6;
                color: #1a1a1a;
            }}
        """)

        # Force Qt to re-evaluate the stylesheet cascade after
        # constructing all properties.
        self.ensurePolished()

        # #region agent log — capture computed geometry after construction
        import time as _time, json as _json
        _log = {
            "sessionId": "d2fb9f", "runId": "initial", "hypothesisId": "H1",
            "location": "info_button.py:QInfoButtonCompact.__init__",
            "message": "info_button_constructed",
            "data": {
                "size": size, "radius": radius,
                "objectName": self.objectName(),
                "isFlat": self.isFlat(),
                "geometry": {"w": self.width(), "h": self.height()},
                "fixedSize": {"w": self.maximumWidth(), "h": self.maximumHeight()},
                "hasStyleSheet": bool(self.styleSheet()),
            },
            "timestamp": _time.time() * 1000,
        }
        try:
            with open("debug-d2fb9f.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps(_log) + "\n")
        except Exception:
            pass
        # #endregion

        self.clicked.connect(self._toggle_popup)

    def set_help_text(self, text: str) -> None:
        """Update the help text displayed in the popup."""
        self._help_text = text

    def help_text(self) -> str:
        """Return the current help text."""
        return self._help_text

    def _toggle_popup(self) -> None:
        """Show or hide the info popup."""
        if self._popup is not None and self._popup.isVisible():
            self._popup.hide()
            self._popup = None
            return

        if not self._help_text.strip():
            return

        self._popup = QInfoPopup(
            text=self._help_text,
            max_width=self._popup_max_width,
            max_height=self._popup_max_height,
        )
        self._popup.show_at_button(self)

    def hide_popup(self) -> None:
        """Hide the popup if it's visible."""
        if self._popup is not None:
            self._popup.hide()
            self._popup = None


__all__ = ["QInfoPopup", "QInfoButton", "QInfoButtonCompact"]
