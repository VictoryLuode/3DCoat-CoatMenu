"""Clipped viewport with tumbler animation for QDialEnumPicker."""
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

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QWidget

from ported.lks_utils.gui_qt.widgets.dial_enum_option import DialEnumOption
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_metrics import ANIMATION_MS, ADORNMENT_SIZE_PX
from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.option_row_widget import (
    _DialEnumOptionRowWidget,
)


class _DialEnumValueViewport(QWidget):
    """Shows one option row with vertical slide transitions."""

    clicked = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        adornment_px: int = ADORNMENT_SIZE_PX,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dial_enum_value_viewport")
        self._adornment_px = max(1, adornment_px)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._text_color: str = "#f0f0f0"
        self._hovered: bool = False
        self._current_row: _DialEnumOptionRowWidget | None = None
        self._outgoing_row: _DialEnumOptionRowWidget | None = None
        self._animation_enabled: bool = True
        self._active_animation: QPropertyAnimation | None = None

    def set_colors(self, *, bg: str, hover: str, text: str) -> None:
        """Apply label colours; chrome fill is painted by QDialEnumPicker."""
        del bg, hover
        self._text_color = text
        if self._current_row is not None:
            self._current_row.apply_text_color(text)
        self.update()

    def is_hovered(self) -> bool:
        """Return whether the pointer is over the value region."""
        return self._hovered

    def set_animation_enabled(self, enabled: bool) -> None:
        """Enable or disable tumbler animation."""
        self._animation_enabled = enabled

    def show_option(
        self,
        option: DialEnumOption,
        *,
        animate: bool = True,
        direction: int = 1,
    ) -> None:
        """Display *option*, optionally animating from the previous row."""
        if self._active_animation is not None:
            self._settle_on(option)
            return
        if self._current_row is None or not animate or not self._animation_enabled:
            self._settle_on(option)
            return
        if self._prefers_reduced_motion():
            self._settle_on(option)
            return

        self._start_slide(option, direction=direction)

    def _make_row(self, option: DialEnumOption) -> _DialEnumOptionRowWidget:
        row = _DialEnumOptionRowWidget(
            option,
            parent=self,
            display_only=True,
            text_color=self._text_color,
            adornment_px=self._adornment_px,
        )
        return row

    def _settle_on(self, option: DialEnumOption) -> None:
        self._purge_row_widgets()
        row = self._make_row(option)
        row.setGeometry(self._content_rect())
        row.show()
        self._current_row = row
        self.update()

    def _start_slide(self, option: DialEnumOption, *, direction: int) -> None:
        self._stop_animation()

        outgoing = self._current_row
        if outgoing is not None:
            outgoing.show()

        incoming = self._make_row(option)
        content_h = self._content_rect().height()
        if direction >= 0:
            outgoing_end = -content_h
            incoming_start = content_h
        else:
            outgoing_end = content_h
            incoming_start = -content_h

        incoming.setGeometry(self._content_rect(incoming_start))
        incoming.show()

        self._outgoing_row = outgoing
        self._current_row = incoming

        anim = QPropertyAnimation(self)
        anim.setDuration(ANIMATION_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _on_value(value: float) -> None:
            if outgoing is not None:
                y = int(outgoing_end * value)
                outgoing.setGeometry(self._content_rect(y))
            y_in = int(incoming_start + (0 - incoming_start) * value)
            incoming.setGeometry(self._content_rect(y_in))
            self.update()

        def _on_finished() -> None:
            self._finish_slide(outgoing, incoming)

        anim.valueChanged.connect(_on_value)
        anim.finished.connect(_on_finished)
        self._active_animation = anim
        anim.start()

    def _finish_slide(
        self,
        outgoing: _DialEnumOptionRowWidget | None,
        incoming: _DialEnumOptionRowWidget,
    ) -> None:
        if outgoing is not None:
            outgoing.hide()
            outgoing.setParent(None)
            outgoing.deleteLater()
        self._outgoing_row = None
        incoming.setGeometry(self._content_rect())
        self._active_animation = None
        self.update()

    def _content_rect(self, y_offset: int = 0) -> QRect:
        margins = self.contentsMargins()
        return QRect(
            margins.left(),
            margins.top() + y_offset,
            max(1, self.width() - margins.left() - margins.right()),
            max(1, self.height() - margins.top() - margins.bottom()),
        )

    def _stop_animation(self) -> None:
        if self._active_animation is None:
            return
        self._active_animation.stop()
        self._active_animation.deleteLater()
        self._active_animation = None

    def _purge_row_widgets(self) -> None:
        """Hide and detach all row widgets immediately (prevents paint cruft)."""
        self._stop_animation()
        for child in self.findChildren(
            _DialEnumOptionRowWidget,
            options=Qt.FindChildOption.FindDirectChildrenOnly,
        ):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self._current_row = None
        self._outgoing_row = None
        self.update()

    def resizeEvent(self, event: object) -> None:
        if self._current_row is not None and self._active_animation is None:
            self._current_row.setGeometry(self._content_rect())
        super().resizeEvent(event)

    def enterEvent(self, event: object) -> None:
        self._hovered = True
        self._repaint_picker_chrome()
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:
        self._hovered = False
        self._repaint_picker_chrome()
        super().leaveEvent(event)

    def _repaint_picker_chrome(self) -> None:
        picker = self.parentWidget()
        if picker is not None:
            picker.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    @staticmethod
    def _prefers_reduced_motion() -> bool:
        try:
            return QGuiApplication.styleHints().useReduceMotion()
        except Exception:
            return False
