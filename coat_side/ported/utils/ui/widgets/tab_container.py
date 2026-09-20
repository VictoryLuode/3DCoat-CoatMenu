"""
Tab Container - Standardised tab body widget and legacy factory.

Provides two entry points:

*StandardTabBody* — the recommended widget for all tabs.  It owns:
  - A header ribbon with a left-aligned title and optional right-aligned info
    (``?``) button.
  - A scrollable content area (QSmoothScrollArea, scrollbar as needed) whose children
    are top-aligned and expand to fill available space.
  - A ``content_layout`` property where tab-specific widgets are added.

*create_tab_with_revert* — legacy factory kept for backward compatibility.
  Wraps a StandardTabBody in a TabContainer so existing callers that use
  ``tab.content_layout`` / ``tab.widget`` continue to work.

Usage (new code):
    from ported.utils.ui.widgets.tab_container import StandardTabBody

    body = StandardTabBody(title="My Tab", info_tooltip="Help text")
    body.content_layout.addWidget(my_section)
    return body  # StandardTabBody IS a QWidget

Usage (backward compat):
    from ported.utils.ui.widgets import create_tab_with_revert

    tab = create_tab_with_revert(title="Tools")
    tab.content_layout.addWidget(my_section)
    return tab.widget
"""
from __future__ import annotations

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget, QVBoxLayout

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QSizePolicy,
    )
    from PySide6.QtCore import Qt
    from ported.lks_utils.gui_qt.widgets.smooth_scroll_area import QSmoothScrollArea

    HAS_QT: bool = True
except ImportError:
    HAS_QT = False


# =============================================================================
# CONSTANTS
# =============================================================================

_HEADER_HEIGHT: int = 28
_INFO_BUTTON_SIZE: int = 22


# =============================================================================
# StandardTabBody
# =============================================================================

class StandardTabBody(QWidget):
    """Consistent tab body widget — header ribbon + scrollable content area.

    Every tab in the LKS panel should use this so all tabs share the same
    visual structure: a dark header ribbon with title and optional help
    button, followed by a scroll area whose children are top-aligned.

    Layout::
        ┌─────────────────────────────────────┐
        │ Header Ribbon (HBox, 28px)           │
        │ ┌──────────────┐┌──┐                 │
        │ │ Title Label  ││? │ ← stretcher →   │
        │ └──────────────┘└──┘                 │
        ├─────────────────────────────────────┤
        │ QSmoothScrollArea (stretch=1)       │
        │ ┌─────────────────────────────────┐ │
        │ │ Content widget                   │ │
        │ │ QVBoxLayout, AlignTop            │ │
        │ │ - child widgets added here       │ │
        │ │ - stretch at bottom              │ │
        │ └─────────────────────────────────┘ │
        └─────────────────────────────────────┘
    """

    def __init__(
        self,
        title: str = "",
        info_tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Create a standardised tab body.

        Args:
            title: Tab title displayed in the header ribbon (left-aligned).
            info_tooltip: Rich-text help text for the ``?`` button.  The
                button is hidden when the string is empty.
            parent: Optional parent widget.
        """
        if not HAS_QT:
            raise ImportError("PySide6 is required for StandardTabBody")

        super().__init__(parent)
        self._title: str = title
        self._info_tooltip: str = info_tooltip

        # ── outer layout ──────────────────────────────────────────────
        outer: QVBoxLayout = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── header ribbon ─────────────────────────────────────────────
        self._header: QWidget = self._build_header()
        outer.addWidget(self._header)

        # ── scrollable content area ───────────────────────────────────
        self._scroll: QSmoothScrollArea = QSmoothScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QSmoothScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._content_widget: QWidget = QWidget()
        self._content_layout: QVBoxLayout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._content_widget)
        outer.addWidget(self._scroll, 1)

    # ── header builder ──────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        """Build the header ribbon with title (left) and info button (right)."""
        header: QWidget = QWidget()
        header.setObjectName("_lks_tab_header")
        header.setFixedHeight(_HEADER_HEIGHT)
        header.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        # Use object-name selector so styles do NOT cascade to children
        # (prevents QWidget rules from overriding QInfoButtonCompact styles)
        header.setStyleSheet(f"""
            QWidget#_lks_tab_header {{
                background-color: #383838;
                border-bottom: 1px solid #444444;
                border-radius: 0px;
            }}
        """)

        row: QHBoxLayout = QHBoxLayout(header)
        row.setContentsMargins(8, 0, 6, 0)
        row.setSpacing(6)

        # Title label (left)
        title_label: QLabel = QLabel(self._title)
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #90caf9;
            background: transparent;
            border: none;
            padding: 0px;
        """)
        row.addWidget(title_label)

        # Info button — right next to the title, before the spacer
        if self._info_tooltip.strip():
            from .info_button import InfoButtonCompact
            info_btn: InfoButtonCompact = InfoButtonCompact(
                help_text=self._info_tooltip,
                parent=header,
            )
            row.addWidget(info_btn)

            # #region agent log
            import time as _time2, json as _json2
            # Check parent stylesheet cascade by walking up
            _parent_chain: list[str] = []
            _w = info_btn
            for _ in range(5):
                _p = _w.parentWidget()
                if _p is None:
                    break
                _ss = _p.styleSheet()
                _parent_chain.append(f"{_p.__class__.__name__}(ss_len={len(_ss)})")
                _w = _p
            _log_payload = {
                "sessionId": "d2fb9f",
                "runId": "initial",
                "hypothesisId": "H1",
                "location": "tab_container.py:183",
                "message": "info_button_in_tab_header",
                "data": {
                    "objectName": info_btn.objectName(),
                    "isFlat": info_btn.isFlat(),
                    "geometry": {"w": info_btn.width(), "h": info_btn.height()},
                    "sizePolicy": str(info_btn.sizePolicy()),
                    "parentChain": _parent_chain,
                    "selfStyleSheetLen": len(info_btn.styleSheet()),
                },
                "timestamp": _time2.time() * 1000,
            }
            try:
                with open("debug-d2fb9f.log", "a", encoding="utf-8") as _f:
                    _f.write(_json2.dumps(_log_payload) + "\n")
            except Exception:
                pass
            # #endregion

        # Spacer — pushes remaining space to the right
        row.addStretch()

        return header

    # ── properties ──────────────────────────────────────────────────────────

    @property
    def content_layout(self) -> QVBoxLayout:
        """The QVBoxLayout inside the scroll area. Add widgets here."""
        return self._content_layout

    @property
    def title(self) -> str:
        """The current header title text."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value
        # Find the QLabel inside the header and update it
        header_layout = self._header.layout()
        if header_layout is not None and header_layout.count() > 0:
            item = header_layout.itemAt(0)
            if item is not None:
                label = item.widget()
                if isinstance(label, QLabel):
                    label.setText(value)

    def set_info_tooltip(self, text: str) -> None:
        """Update the help text for the info button."""
        self._info_tooltip = text
        # Reconstruction would be needed if text is set after construction,
        # but in practice this is rare.  If needed, we could rebuild the header.


# =============================================================================
# TabContainer (backward compat)
# =============================================================================

class TabContainer:
    """
    Legacy container for tab content.

    Attributes:
        widget: The main QWidget for the tab
        content_layout: QVBoxLayout where tab content should be added

    Prefer ``StandardTabBody`` for new code.  This class exists to keep
    the ``create_tab_with_revert`` return type stable for existing callers.
    """
    def __init__(self, widget: QWidget, content_layout: QVBoxLayout):
        self.widget = widget
        self.content_layout = content_layout


# =============================================================================
# create_tab_with_revert (legacy factory)
# =============================================================================

def create_tab_with_revert(
    log_success: Callable[[str], None] | None = None,
    log_error: Callable[[str], None] | None = None,
    title: str | None = None,
    scrollable: bool = True,
    info_tooltip: str = "",
) -> TabContainer:
    """
    Create a tab container using the StandardTabBody widget.

    Args:
        log_success: (unused, kept for backward compat)
        log_error: (unused, kept for backward compat)
        title: Optional title for the tab header ribbon
        scrollable: Whether to wrap content in a scroll area (always True)
        info_tooltip: Optional help text for the ``?`` button

    Returns:
        TabContainer with ``.widget`` (the StandardTabBody) and
        ``.content_layout`` (the scroll area's inner layout).

    Example:
        tab = create_tab_with_revert(title="Tools", info_tooltip="Help text")
        tab.content_layout.addWidget(my_section)
        return tab.widget
    """
    if not HAS_QT:
        raise ImportError("PySide6 is required for tab containers")

    body: StandardTabBody = StandardTabBody(
        title=title or "",
        info_tooltip=info_tooltip,
    )

    return TabContainer(body, body.content_layout)
