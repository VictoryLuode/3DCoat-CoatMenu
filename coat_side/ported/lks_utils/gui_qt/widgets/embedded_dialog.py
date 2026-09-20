"""Embedded modal dialog overlay widget for PySide6.

A QFrame that overlays inside a parent widget, providing a modal
dialog experience without creating a separate top-level window.
Useful when the parent has ``WindowStaysOnTopHint`` set, which
causes standard QMessageBox to appear behind the panel.

Usage (synchronous)::

    dialog = QEmbeddedDialog(
        parent=my_panel,
        title="Confirm",
        message="Are you sure?",
        buttons=BUTTONS_YES_NO,
    )
    result = dialog.exec_()
    if result == DialogButton.YES:
        do_something()

Usage (asynchronous)::

    dialog = QEmbeddedDialog(
        parent=my_panel,
        title="Confirm",
        message="Continue?",
        buttons=BUTTONS_OK_CANCEL,
    )
    dialog.done.connect(lambda btn: print(f"Clicked {btn}"))
    dialog.show()
"""

from __future__ import annotations

from enum import IntEnum
from functools import partial
from typing import ClassVar

from PySide6.QtCore import (
    QEvent,
    QEventLoop,
    QObject,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


# =============================================================================
# CONSTANTS
# =============================================================================

_CARD_BG: str = "#2b2b2b"
_CARD_BORDER: str = "#444444"
_CARD_RADIUS: int = 8

_TITLE_BAR_HEIGHT: int = 32
_CARD_PADDING_H: int = 24
_CARD_PADDING_V: int = 16
_CARD_MIN_WIDTH: int = 320
_CARD_MAX_WIDTH: int = 520
_BUTTON_SPACING: int = 8
_CLOSE_BTN_SIZE: int = 24

# Text / accent colors
_COLOR_TEXT: str = "#ddd"
_COLOR_TEXT_SECONDARY: str = "#ccc"
_COLOR_TEXT_MUTED: str = "#888"
_COLOR_ACCENT: str = "#90caf9"
_COLOR_BG_HOVER: str = "#3a3a3a"

# =============================================================================
# ENUMS
# =============================================================================


class DialogButton(IntEnum):
    """Standard dialog button roles."""

    OK = 0
    CANCEL = 1
    YES = 2
    NO = 3
    CLOSE = 4


class DialogAction(IntEnum):
    """Predefined button configurations."""

    OK = 0
    OK_CANCEL = 1
    YES_NO = 2


# =============================================================================
# PREDEFINED BUTTON SETS
# =============================================================================

BUTTONS_OK: list[tuple[str, DialogButton]] = [
    ("OK", DialogButton.OK),
]
BUTTONS_OK_CANCEL: list[tuple[str, DialogButton]] = [
    ("OK", DialogButton.OK),
    ("Cancel", DialogButton.CANCEL),
]
BUTTONS_YES_NO: list[tuple[str, DialogButton]] = [
    ("Yes", DialogButton.YES),
    ("No", DialogButton.NO),
]
BUTTONS_CLOSE: list[tuple[str, DialogButton]] = [
    ("Close", DialogButton.CLOSE),
]

_DIALOG_ACTION_MAP: dict[DialogAction, list[tuple[str, DialogButton]]] = {
    DialogAction.OK: BUTTONS_OK,
    DialogAction.OK_CANCEL: BUTTONS_OK_CANCEL,
    DialogAction.YES_NO: BUTTONS_YES_NO,
}


# =============================================================================
# QEmbeddedDialog
# =============================================================================


class QEmbeddedDialog(QFrame):
    """Modal dialog overlay embedded inside a parent widget.

    Unlike ``QMessageBox``, this widget is placed as a child of a
    parent container rather than as a separate top-level window.  This
    ensures it stays on top even when the parent has
    ``WindowStaysOnTopHint`` enabled.

    Attributes:
        done: Signal emitted with the ``DialogButton`` that was clicked.
    """

    done: ClassVar[Signal] = Signal(
        DialogButton
    )  # type: ignore[assignment,misc]

    def __init__(
        self,
        parent: QWidget,
        *,
        title: str = "",
        message: str = "",
        buttons: list[tuple[str, DialogButton]] | DialogAction | None = None,
    ) -> None:
        """Initialise the embedded dialog.

        Args:
            parent: The parent widget to overlay within.
            title: Optional title bar text.
            message: Message text (supports plain text or rich HTML).
            buttons: Either a ``DialogAction`` enum for a predefined
                set, or a list of ``(label, DialogButton)`` tuples.
                Defaults to ``DialogAction.OK``.
        """
        super().__init__(parent)
        self._parent: QWidget = parent
        self._result: DialogButton | None = None
        self._loop: QEventLoop | None = None

        # Resolve buttons
        if buttons is None:
            buttons = DialogAction.OK
        if isinstance(buttons, DialogAction):
            self._buttons: list[tuple[str, DialogButton]] = _DIALOG_ACTION_MAP[buttons]
        else:
            self._buttons = buttons

        self.setObjectName("_lksEmbeddedDialogOverlay")
        self.setGeometry(parent.rect())
        self.hide()

        # ---- Semi-transparent backdrop ----
        self.setAutoFillBackground(True)
        palette: QPalette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0, 180))
        self.setPalette(palette)

        # ---- Card widget ----
        self._card: QFrame = QFrame(self)
        self._card.setObjectName("_lksDialogCard")
        self._card.setStyleSheet(
            f"""#_lksDialogCard {{
                background-color: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: {_CARD_RADIUS}px;
            }}"""
        )

        self._build_card(title, message, self._buttons)

        # Let layout compute the card's height, constrain width
        card_w: int = min(_CARD_MAX_WIDTH, parent.width() - 40)
        if card_w < _CARD_MIN_WIDTH:
            card_w = max(parent.width() - 20, 200)
        self._card.setFixedWidth(card_w)
        self._card.adjustSize()

        self._position_card()

        # Track parent resize so the overlay and card stay aligned
        parent.installEventFilter(self)

    # -------------------------------------------------------------------------
    # Build
    # -------------------------------------------------------------------------

    def _build_card(
        self,
        title: str,
        message: str,
        buttons: list[tuple[str, DialogButton]],
    ) -> None:
        """Build the card's internal layout."""
        layout: QVBoxLayout = QVBoxLayout(self._card)
        layout.setContentsMargins(0, 0, 0, _CARD_PADDING_V)
        layout.setSpacing(0)

        # ---- Title bar ----
        if title:
            title_bar: QWidget = QWidget()
            title_bar.setFixedHeight(_TITLE_BAR_HEIGHT)
            tl: QHBoxLayout = QHBoxLayout(title_bar)
            tl.setContentsMargins(_CARD_PADDING_H, 0, 8, 0)
            tl.setSpacing(0)

            tl_label: QLabel = QLabel(title)
            tl_label.setStyleSheet(
                f"font-weight: bold; color: {_COLOR_TEXT}; font-size: 12px;"
            )
            tl.addWidget(tl_label)
            tl.addStretch()

            close_btn: QPushButton = QPushButton("\u2715")
            close_btn.setFixedSize(_CLOSE_BTN_SIZE, _CLOSE_BTN_SIZE)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet(
                f"""QPushButton {{
                    background: transparent;
                    border: none;
                    color: {_COLOR_TEXT_MUTED};
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    color: {_COLOR_TEXT};
                    background: {_COLOR_BG_HOVER};
                    border-radius: 4px;
                }}"""
            )
            close_btn.clicked.connect(lambda: self._resolve(DialogButton.CLOSE))
            tl.addWidget(close_btn)

            layout.addWidget(title_bar)

        # ---- Message ----
        if message:
            msg_label: QLabel = QLabel(message)
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet(
                f"color: {_COLOR_TEXT_SECONDARY}; padding: {_CARD_PADDING_V}px {_CARD_PADDING_H}px;"
                f" font-size: 11px;"
            )
            msg_label.setTextFormat(Qt.TextFormat.AutoText)
            msg_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            layout.addWidget(msg_label)

        # ---- Button row ----
        if buttons:
            btn_layout: QHBoxLayout = QHBoxLayout()
            btn_layout.setContentsMargins(
                _CARD_PADDING_H, _CARD_PADDING_V // 2, _CARD_PADDING_H, 0
            )
            btn_layout.setSpacing(_BUTTON_SPACING)
            btn_layout.addStretch()

            for text, role in buttons:
                btn: QPushButton = QPushButton(text)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    f"""QPushButton {{
                        background-color: {_COLOR_BG_HOVER};
                        border: 1px solid {_CARD_BORDER};
                        border-radius: 4px;
                        padding: 6px 20px;
                        color: {_COLOR_TEXT};
                        font-size: 11px;
                        min-width: 70px;
                    }}
                    QPushButton:hover {{
                        background-color: #4a4a4a;
                        border-color: {_COLOR_ACCENT};
                        color: {_COLOR_ACCENT};
                    }}
                    QPushButton:pressed {{
                        background-color: #333333;
                    }}"""
                )
                btn.clicked.connect(
                    partial(self._resolve, role)
                )
                btn_layout.addWidget(btn)

            btn_layout.addStretch()
            layout.addLayout(btn_layout)

    # -------------------------------------------------------------------------
    # Positioning
    # -------------------------------------------------------------------------

    def _position_card(self) -> None:
        """Centre the card within the parent widget."""
        pw: int = self._parent.width()
        ph: int = self._parent.height()
        cw: int = self._card.width()
        ch: int = self._card.height()
        x: int = max(0, (pw - cw) // 2)
        y: int = max(0, (ph - ch) // 2)
        self._card.move(x, y)

    # -------------------------------------------------------------------------
    # Event filter – track parent resize
    # -------------------------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Keep overlay geometry in sync with the parent widget."""
        if watched is self._parent and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._parent.rect())
            self._position_card()
        return super().eventFilter(watched, event)

    # -------------------------------------------------------------------------
    # Resolution
    # -------------------------------------------------------------------------

    def _resolve(self, result: DialogButton) -> None:
        """Store result, emit signal, quit event loop, and hide."""
        self._result = result
        self.done.emit(result)
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()
        self.hide()
        # Remove parent event filter to avoid dangling callbacks
        self._parent.removeEventFilter(self)
        self.deleteLater()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def result(self) -> DialogButton | None:
        """Return which button was clicked, or ``None`` if not resolved."""
        return self._result

    def exec_(self) -> DialogButton | None:
        """Show the dialog modally and block until the user responds.

        Returns the ``DialogButton`` that was clicked, or ``None`` if the
        dialog was dismissed without a resolution.
        """
        self.show()
        self.raise_()
        self._loop = QEventLoop()
        self._loop.exec()  # blocks until _resolve() calls quit()
        return self._result
