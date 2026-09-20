"""Dropdown popup listing all dial enum options."""

from __future__ import annotations

from collections.abc import Callable

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication, QHideEvent, QShowEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QScrollArea,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.option_row_widget import (
    _DialEnumOptionRowWidget,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_option import DialEnumOption
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_default_theme import (
    DialEnumPickerColors,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_metrics import (
    CHROME_BORDER_RADIUS_PX,
    DEFAULT_ROW_HEIGHT_PX,
    POPUP_ANIMATION_MS,
    POPUP_MAX_VISIBLE_ROWS,
)

_POPUP_GAP_PX: int = 2
_MAX_OPEN_POSITION_RETRIES: int = 5
_POPUP_CONTENT_MARGIN_PX: int = 1


def _anchor_global_below(anchor: QWidget, *, gap_px: int = _POPUP_GAP_PX) -> QPoint | None:
    """Return screen position for the popup's top-left, just under *anchor*.

    Returns ``None`` when the anchor is not yet mapped (``mapToGlobal`` would
    incorrectly yield ``(0, 0)``).
    """
    if not anchor.isVisible():
        return None
    top_level = anchor.window()
    if top_level is None or not top_level.isVisible():
        return None
    if top_level.windowHandle() is None:
        return None

    rect = anchor.rect()
    if rect.width() <= 0 or rect.height() <= 0:
        return None

    anchor.ensurePolished()
    return anchor.mapToGlobal(QPoint(0, rect.height() + gap_px))


def _vertical_scrollbar_extent_px() -> int:
    style = QApplication.style()
    if style is None:
        return 12
    return style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)


class _DialEnumOptionsPopup(QFrame):
    """Frameless popup listing all options with vertical rollout animation."""

    option_chosen = Signal(int)

    def __init__(self) -> None:
        # Top-level popup — parented Qt.Popup windows mis-handle global move().
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("dial_enum_options_popup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._text_color: str = "#f0f0f0"
        self._colors: DialEnumPickerColors | None = None
        self._target_width: int = 0
        self._target_height: int = 0
        self._force_hide: bool = False
        self._hiding: bool = False
        self._height_anim: QVariantAnimation | None = None
        self._anchor: QWidget | None = None
        self._open_retry_count: int = 0
        self._current_index: int = 0
        self._hover_index: int = -1
        self._row_widgets: list[_DialEnumOptionRowWidget] = []

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("dial_enum_options_scroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._rows_host = QWidget()
        self._rows_host.setObjectName("dial_enum_options_rows")
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._scroll.setWidget(self._rows_host)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _POPUP_CONTENT_MARGIN_PX,
            _POPUP_CONTENT_MARGIN_PX,
            _POPUP_CONTENT_MARGIN_PX,
            _POPUP_CONTENT_MARGIN_PX,
        )
        layout.addWidget(self._scroll)

    def set_text_color(self, color: str) -> None:
        """Apply popup row label colour."""
        self._text_color = color

    def apply_theme_colors(
        self,
        colors: DialEnumPickerColors,
        *,
        border_radius_px: int | None = None,
    ) -> None:
        """Apply gray popup chrome; scroll area gets its own sheet to beat global QSS."""
        self._colors = colors
        radius_px = (
            CHROME_BORDER_RADIUS_PX if border_radius_px is None else max(0, border_radius_px)
        )
        self.setStyleSheet(
            "QFrame#dial_enum_options_popup {"
            f"background-color: {colors.popup_bg};"
            f"border: 1px solid {colors.border};"
            f"border-radius: {radius_px}px;"
            "}"
        )
        scrollbar_extent = _vertical_scrollbar_extent_px()
        self._scroll.setStyleSheet(
            "QScrollArea#dial_enum_options_scroll {"
            f"background-color: {colors.popup_bg};"
            "border: 0;"
            "outline: 0;"
            "}"
            "QWidget#dial_enum_options_rows {"
            f"background-color: {colors.popup_bg};"
            "}"
            "QScrollArea#dial_enum_options_scroll QScrollBar:vertical {"
            f"width: {scrollbar_extent}px;"
            f"background: {colors.scrollbar_track};"
            "margin: 0;"
            "border: 0;"
            "}"
            "QScrollArea#dial_enum_options_scroll QScrollBar::handle:vertical {"
            f"background-color: {colors.scrollbar_handle};"
            "min-height: 24px;"
            "border-radius: 3px;"
            "margin: 2px 1px;"
            "}"
            "QScrollArea#dial_enum_options_scroll QScrollBar::add-page:vertical,"
            "QScrollArea#dial_enum_options_scroll QScrollBar::sub-page:vertical {"
            f"background: {colors.scrollbar_track};"
            "}"
            "QScrollArea#dial_enum_options_scroll QScrollBar::add-line:vertical,"
            "QScrollArea#dial_enum_options_scroll QScrollBar::sub-line:vertical {"
            "height: 0;"
            "}"
        )
        self._apply_row_highlights()

    def populate(
        self,
        options: list[DialEnumOption],
        *,
        current_index: int,
        min_width: int,
    ) -> None:
        """Rebuild popup rows."""
        self._clear_rows()
        content_width = min_width
        self._current_index = max(0, min(current_index, max(0, len(options) - 1)))
        self._hover_index = -1

        for index, option in enumerate(options):
            row = _DialEnumOptionRowWidget(
                option,
                parent=self._rows_host,
                display_only=False,
                selectable=True,
                text_color=self._text_color,
            )
            row.clicked.connect(lambda idx=index: self._on_row_clicked(idx))
            row.installEventFilter(self)
            row_hint = row.sizeHint()
            content_width = max(content_width, row_hint.width())
            self._rows_layout.addWidget(row)
            self._row_widgets.append(row)

        row_count = max(1, len(options))
        needs_scroll = row_count > POPUP_MAX_VISIBLE_ROWS
        if needs_scroll:
            self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            content_width += _vertical_scrollbar_extent_px()
        else:
            self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._rows_host.setMinimumWidth(content_width)
        visible_rows = min(row_count, POPUP_MAX_VISIBLE_ROWS)
        height = (visible_rows * DEFAULT_ROW_HEIGHT_PX) + (2 * _POPUP_CONTENT_MARGIN_PX)
        self._target_width = content_width
        self._target_height = height
        self._apply_row_highlights()

    def _clear_rows(self) -> None:
        for row in self._row_widgets:
            row.removeEventFilter(self)
            row.setParent(None)
            row.deleteLater()
        self._row_widgets.clear()
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _apply_row_highlights(self) -> None:
        colors = self._colors
        if colors is None:
            return
        for index, row in enumerate(self._row_widgets):
            if index == self._current_index:
                fill = colors.popup_selected
            elif index == self._hover_index:
                fill = colors.popup_hover
            else:
                fill = colors.popup_bg
            row.apply_row_fill(fill)

    def _reset_list_scroll(self) -> None:
        self._scroll.verticalScrollBar().setValue(0)

    def _scroll_to_current_item(self) -> None:
        """Scroll so the selection is visible without overscroll padding."""
        total = len(self._row_widgets)
        if total == 0:
            self._reset_list_scroll()
            return
        if total <= POPUP_MAX_VISIBLE_ROWS:
            self._reset_list_scroll()
            return

        first_visible_row = max(
            0,
            min(self._current_index - 2, total - POPUP_MAX_VISIBLE_ROWS),
        )
        y_offset = first_visible_row * DEFAULT_ROW_HEIGHT_PX
        bar = self._scroll.verticalScrollBar()
        bar.setValue(min(y_offset, bar.maximum()))

    def dismiss_immediately(self) -> None:
        """Hide without rollout animation (used on owner teardown)."""
        host: QWidget | None = self._anchor
        self._stop_height_animation()
        self._hiding = False
        self._force_hide = True
        self._set_anchor(None)
        self._set_list_interactive(True)
        self._reset_list_scroll()
        super().setVisible(False)
        # Keep _force_hide True through surface teardown so closeEvent accepts.
        self._release_keyboard_surface()
        self._force_hide = False
        self._restore_host_activation(host)

    def open_below(self, anchor: QWidget) -> None:
        """Show popup under *anchor* with a downward rollout."""
        self._stop_height_animation()
        self._hiding = False
        self._set_anchor(anchor)
        self._open_retry_count = 0
        self._open_below_when_ready()

    def _set_anchor(self, anchor: QWidget | None) -> None:
        previous = self._anchor
        if previous is not None:
            try:
                previous.destroyed.disconnect(self._on_anchor_destroyed)
            except (RuntimeError, TypeError):
                pass
        self._anchor = anchor
        if anchor is not None:
            anchor.destroyed.connect(self._on_anchor_destroyed)

    def _on_anchor_destroyed(self, *_args: object) -> None:
        self.dismiss_immediately()

    def _open_below_when_ready(self) -> None:
        anchor = self._anchor
        if anchor is None:
            return

        global_pos = _anchor_global_below(anchor)
        if global_pos is None:
            if self._open_retry_count < _MAX_OPEN_POSITION_RETRIES:
                self._open_retry_count += 1
                QTimer.singleShot(0, self._open_below_when_ready)
            return

        self._stop_height_animation()
        self._apply_final_geometry()
        self._scroll_to_current_item()
        self._move_to_global(global_pos)

        if self._prefers_reduced_motion():
            self._apply_reveal_height(self._target_height)
            self.setVisible(True)
            self._move_to_global(global_pos)
            self._set_list_interactive(True)
            self._scroll.setFocus(Qt.FocusReason.PopupFocusReason)
            return

        self._set_list_interactive(False)
        self._apply_reveal_height(0)
        self.setVisible(True)
        self._move_to_global(global_pos)
        self._run_reveal_animation(
            0,
            self._target_height,
            easing=QEasingCurve.Type.OutCubic,
            on_finished=self._focus_list,
        )

    def showEvent(self, event: QShowEvent) -> None:
        """Re-sync position once the popup is mapped (guards early open races)."""
        super().showEvent(event)
        if self._height_anim is not None:
            return
        anchor = self._anchor
        if anchor is None:
            return
        global_pos = _anchor_global_below(anchor)
        if global_pos is not None:
            self._move_to_global(global_pos)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Qt.Popup click-outside often closes before our setVisible(False) runs."""
        if self._force_hide:
            super().closeEvent(event)
            return
        event.ignore()
        if self.isVisible():
            self._animate_hide()

    def hideEvent(self, event: QHideEvent) -> None:
        """Replay retract animation when Qt dismisses the popup instantly."""
        if self._force_hide:
            super().hideEvent(event)
            return
        if self._hiding:
            super().hideEvent(event)
            return
        super().hideEvent(event)
        if self._target_height <= 0:
            return
        QTimer.singleShot(0, self._replay_retract_after_external_dismiss)

    def setVisible(self, visible: bool) -> None:  # noqa: N802 — Qt API name
        """Intercept hide so popup collapses before dismissal."""
        if visible:
            self._force_hide = False
            self._hiding = False
            super().setVisible(True)
            return
        if not self.isVisible():
            return
        if self._force_hide:
            self._set_anchor(None)
            super().setVisible(False)
            return
        self._animate_hide()

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:  # noqa: N802
        if watched in self._row_widgets:
            if event.type() == QEvent.Type.Enter:
                self._hover_index = self._row_widgets.index(watched)
                self._apply_row_highlights()
            elif event.type() == QEvent.Type.Leave:
                self._hover_index = -1
                self._apply_row_highlights()
        return super().eventFilter(watched, event)

    def _replay_retract_after_external_dismiss(self) -> None:
        if self._force_hide or self._hiding or self.isVisible():
            return
        self._hiding = True
        self._set_list_interactive(False)
        self.setUpdatesEnabled(False)
        try:
            self._apply_reveal_height(self._target_height)
            super().setVisible(True)
            self._run_reveal_animation(
                self._target_height,
                0,
                easing=QEasingCurve.Type.InCubic,
                on_finished=self._complete_hide,
            )
        finally:
            self.setUpdatesEnabled(True)

    def _animate_hide(self) -> None:
        if self._hiding:
            return
        self._stop_height_animation()
        if self._prefers_reduced_motion():
            self._force_hide = True
            host: QWidget | None = self._anchor
            self._set_anchor(None)
            super().setVisible(False)
            self._release_keyboard_surface()
            self._force_hide = False
            self._restore_host_activation(host)
            return

        self._hiding = True
        self._set_list_interactive(False)
        start_height = self._current_reveal_height_px()
        self._run_reveal_animation(
            start_height,
            0,
            easing=QEasingCurve.Type.InCubic,
            on_finished=self._complete_hide,
        )

    def _current_reveal_height_px(self) -> int:
        return max(0, min(self.height(), self._target_height))

    def _complete_hide(self) -> None:
        host: QWidget | None = self._anchor
        self._force_hide = True
        self._set_anchor(None)
        self._set_list_interactive(True)
        self._reset_list_scroll()
        super().setVisible(False)
        # Must release while _force_hide is True: closeEvent ignores otherwise,
        # leaving a zombie QWindow that keeps eating KeyPress.
        self._release_keyboard_surface()
        self._force_hide = False
        self._hiding = False
        self._restore_host_activation(host)

    def _release_keyboard_surface(self) -> None:
        """Destroy the hidden popup's platform window so it cannot keep keys.

        ``closeEvent`` ignores closes unless ``_force_hide`` is set, so a plain
        ``QWindow.close()`` leaves a zombie window as ``focusWindow`` that still
        receives KeyPress after Label already has Qt ``focusWidget``. Call this
        while ``_force_hide`` is True; the next show recreates the window.
        """
        self._scroll.clearFocus()
        self.clearFocus()
        if self.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
            self.destroy(destroyWindow=True, destroySubWindows=True)

    def _move_to_global(self, global_pos: QPoint) -> None:
        self.move(global_pos)
        self.raise_()
        # Do NOT activateWindow() here. In multi-window hosts (e.g. 3DCoat + a
        # separate Qt panel), activating this Qt.Popup steals OS focus from the
        # panel; on dismiss Windows restores the host app instead, so panel
        # QLineEdits stop receiving keystrokes until something reactivates them.
        # Qt.Popup already receives input via popup grab + setFocus on the list.

    def _restore_host_activation(self, host: QWidget | None) -> None:
        """Return focus to the picker host after popup closes."""
        if host is None or not isValid(host):
            return
        window = host.window()
        if window is not None and isValid(window):
            window.raise_()
            window.activateWindow()
            win_handle = window.windowHandle()
            if win_handle is not None:
                win_handle.requestActivate()
        host.setFocus(Qt.FocusReason.PopupFocusReason)

    def _apply_final_geometry(self) -> None:
        """Lay out popup and list once at the final size (no per-frame relayout)."""
        self.setFixedSize(self._target_width, self._target_height)
        inner_height = max(
            0,
            self._target_height - (2 * _POPUP_CONTENT_MARGIN_PX),
        )
        self._scroll.setFixedHeight(inner_height)
        self._scroll.setMinimumHeight(inner_height)
        self._scroll.setMaximumHeight(inner_height)

    def _apply_reveal_height(self, visible_px: int) -> None:
        """Reveal only the top *visible_px* by clipping the outer frame height.

        The scroll area keeps its final inner height; Qt clips overflowing
        content instead of using ``setMask`` (which flickers on Windows).
        """
        visible_px = max(0, min(int(visible_px), self._target_height))
        self.setFixedSize(self._target_width, visible_px)

    def _run_reveal_animation(
        self,
        start: int,
        end: int,
        *,
        easing: QEasingCurve.Type,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        self._apply_reveal_height(start)
        anim = QVariantAnimation(self)
        anim.setDuration(POPUP_ANIMATION_MS)
        anim.setStartValue(float(start))
        anim.setEndValue(float(end))
        anim.setEasingCurve(easing)
        anim.valueChanged.connect(
            lambda value: self._apply_reveal_height(int(value))
        )

        def _on_anim_finished() -> None:
            self._height_anim = None
            if on_finished is not None:
                on_finished()

        anim.finished.connect(_on_anim_finished)
        self._height_anim = anim
        anim.start()

    def _stop_height_animation(self) -> None:
        if self._height_anim is None:
            return
        self._height_anim.stop()
        self._height_anim.deleteLater()
        self._height_anim = None

    def _set_list_interactive(self, interactive: bool) -> None:
        self._scroll.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            not interactive,
        )

    def _focus_list(self) -> None:
        self._set_list_interactive(True)
        self._scroll.setFocus(Qt.FocusReason.PopupFocusReason)

    def _on_row_clicked(self, index: int) -> None:
        self.option_chosen.emit(index)
        self.setVisible(False)

    @staticmethod
    def _prefers_reduced_motion() -> bool:
        try:
            return QGuiApplication.styleHints().useReduceMotion()
        except Exception:
            return False
