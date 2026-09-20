"""Stacked up/down stepper buttons for QDialEnumPicker."""

from __future__ import annotations

from typing import Literal

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

StepperHover = Literal["none", "up", "down"]


class _DialEnumStepperColumn(QWidget):
    """Two stacked step buttons on the right edge."""

    step_prev = Signal()
    step_next = Signal()

    def __init__(self, *, width_px: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dial_enum_stepper")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setFixedWidth(width_px)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._up_button = QPushButton("▲", self)
        self._up_button.setObjectName("dial_enum_stepper_up")
        self._up_button.setToolTip("Previous option")
        self._up_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._up_button.setFlat(True)

        self._down_button = QPushButton("▼", self)
        self._down_button.setObjectName("dial_enum_stepper_down")
        self._down_button.setToolTip("Next option")
        self._down_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._down_button.setFlat(True)

        self._up_button.clicked.connect(self.step_prev.emit)
        self._down_button.clicked.connect(self.step_next.emit)

        layout.addWidget(self._up_button, 1)
        layout.addWidget(self._down_button, 1)

        self._up_button.installEventFilter(self)
        self._down_button.installEventFilter(self)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable both step buttons."""
        self._up_button.setEnabled(enabled)
        self._down_button.setEnabled(enabled)

    def apply_style(self, *, text_color: str) -> None:
        """Apply themed text colour; chrome is painted by QDialEnumPicker."""
        shared = (
            "QPushButton#dial_enum_stepper_up,"
            "QPushButton#dial_enum_stepper_down {"
            f"color: {text_color};"
            "background: transparent;"
            "border: 0;"
            "outline: 0;"
            "padding: 0;"
            "margin: 0;"
            "min-width: 0;"
            "max-width: 9999px;"
            "min-height: 0;"
            "font-size: 8px;"
            "}"
            "QPushButton#dial_enum_stepper_up:hover,"
            "QPushButton#dial_enum_stepper_down:hover,"
            "QPushButton#dial_enum_stepper_up:pressed,"
            "QPushButton#dial_enum_stepper_down:pressed {"
            f"color: {text_color};"
            "background: transparent;"
            "}"
        )
        self._up_button.setStyleSheet(shared)
        self._down_button.setStyleSheet(shared)
        self.setStyleSheet("background: transparent; border: 0;")

    def hover_region(self) -> StepperHover:
        """Return which stepper half is under the pointer."""
        if not self.isEnabled():
            return "none"
        if self._down_button.underMouse():
            return "down"
        if self._up_button.underMouse():
            return "up"
        return "none"

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched in (self._up_button, self._down_button) and event.type() in (
            QEvent.Type.Enter,
            QEvent.Type.Leave,
            QEvent.Type.HoverMove,
        ):
            picker = self.parentWidget()
            if picker is not None:
                picker.update()
        return super().eventFilter(watched, event)
