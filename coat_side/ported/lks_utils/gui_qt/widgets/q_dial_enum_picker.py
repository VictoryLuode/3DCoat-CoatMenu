"""Padlock-style enum picker with dial stepping and optional adornments."""
from __future__ import annotations

from typing import Any, Sequence

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QHideEvent,
    QKeyEvent,
    QKeySequence,
    QPaintEvent,
    QPainter,
    QShowEvent,
    QWheelEvent,
)
from shiboken6 import isValid
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.chrome_painter import (
    paint_dial_enum_chrome,
)

from ported.lks_utils.gui_qt.input_bindings_qt import BindingsAwareMixin
from ported.lks_utils.gui_qt.theme import ThemeAwareMixin
from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider
from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.options_popup import (
    _DialEnumOptionsPopup,
)
from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.row_metrics import (
    shrink_to_largest_size,
)
from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.stepper_column import (
    _DialEnumStepperColumn,
)
from ported.lks_utils.gui_qt.widgets._q_dial_enum_picker.value_viewport import (
    _DialEnumValueViewport,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_option import (
    DialEnumOption,
    DialEnumSizeMode,
    normalize_dial_enum_options,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_actions import (
    DIAL_ENUM_OPEN_LIST,
    DIAL_ENUM_STEP_NEXT,
    DIAL_ENUM_STEP_PREV,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_default_theme import (
    DialEnumPickerColors,
    resolve_dial_enum_picker_colors,
)
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_metrics import (
    ADORNMENT_SIZE_PX,
    CHROME_BORDER_RADIUS_PX,
    DEFAULT_ROW_HEIGHT_PX,
    EMPTY_LABEL,
    HORIZONTAL_PADDING_PX,
    STEPPER_WIDTH_PX,
    VERTICAL_PADDING_PX,
)
from ported.lks_utils.input import InputBindings, get_default_bindings
from ported.lks_utils.input.qt_adapter import wheel_event_pair
from ported.lks_utils.theme.theme import Theme


class QDialEnumPicker(ThemeAwareMixin, BindingsAwareMixin, QWidget):
    """Enum picker with padlock-style stepping and optional row adornments."""

    value_changed = Signal(object)
    current_index_changed = Signal(int)

    def __init__(
        self,
        options: Sequence[str | Any | DialEnumOption] = (),
        *,
        current_index: int = 0,
        width: int | None = None,
        height: int | None = None,
        size_mode: DialEnumSizeMode = DialEnumSizeMode.FIXED,
        wrap: bool = False,
        chrome_border_radius_px: int | None = None,
        adornment_px: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dial_enum_picker")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)
        self._chrome_colors: DialEnumPickerColors = resolve_dial_enum_picker_colors(
            QThemeProvider.instance().current()
        )
        self._bindings: InputBindings = get_default_bindings()
        self._options: list[DialEnumOption] = normalize_dial_enum_options(options)
        self._current_index: int = 0
        self._size_mode = size_mode
        self._wrap = wrap
        self._fixed_width = width
        self._fixed_height = height
        self._adornment_px = (
            ADORNMENT_SIZE_PX if adornment_px is None else max(1, adornment_px)
        )
        self._chrome_border_radius_px = (
            CHROME_BORDER_RADIUS_PX
            if chrome_border_radius_px is None
            else max(0, chrome_border_radius_px)
        )

        self._viewport = _DialEnumValueViewport(self, adornment_px=self._adornment_px)
        self._stepper = _DialEnumStepperColumn(width_px=STEPPER_WIDTH_PX, parent=self)
        self._popup = _DialEnumOptionsPopup()
        self.destroyed.connect(self._teardown_popup)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._viewport, 1)
        layout.addWidget(self._stepper, 0)

        self._viewport.clicked.connect(self._open_popup)
        self._stepper.step_prev.connect(lambda: self._step(-1))
        self._stepper.step_next.connect(lambda: self._step(1))
        self._popup.option_chosen.connect(self._choose_index)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if self._options:
            self._current_index = max(0, min(current_index, len(self._options) - 1))
        self.on_theme_changed(QThemeProvider.instance().current())
        self._apply_fixed_geometry()
        self._refresh_display(animate=False)
        self._refresh_enabled_state()

    def options(self) -> list[DialEnumOption]:
        """Return normalized option rows."""
        return list(self._options)

    def current_index(self) -> int:
        """Return the selected option index."""
        return self._current_index

    def current_value(self) -> Any:
        """Return the selected option value."""
        if not self._options:
            return None
        return self._options[self._current_index].value

    def set_options(self, options: Sequence[str | Any | DialEnumOption]) -> None:
        """Replace all options and reclamp the current index."""
        self._options = normalize_dial_enum_options(options)
        if not self._options:
            self._current_index = 0
        else:
            self._current_index = min(self._current_index, len(self._options) - 1)
        self._apply_fixed_geometry()
        self._refresh_display(animate=False)
        self._refresh_enabled_state()

    def set_value(self, value: Any, *, animate: bool = True) -> None:
        """Select the option whose identity matches *value*."""
        for index, option in enumerate(self._options):
            if option.value == value:
                self.set_current_index(index, animate=animate)
                return

    def set_current_index(self, index: int, *, animate: bool = True) -> None:
        """Select option by index."""
        if not self._options:
            self._current_index = 0
            self._refresh_display(animate=False)
            return
        clamped = max(0, min(index, len(self._options) - 1))
        if clamped == self._current_index:
            return
        direction = 1 if clamped > self._current_index else -1
        self._current_index = clamped
        self._refresh_display(animate=animate, direction=direction)
        self.value_changed.emit(self.current_value())
        self.current_index_changed.emit(self._current_index)

    def set_wrap(self, wrap: bool) -> None:
        """Enable or disable wrap-around stepping."""
        self._wrap = wrap

    def resync_geometry(self) -> None:
        """Re-measure shrink-to-largest width after font/theme changes."""
        if self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST:
            self._sync_shrink_to_largest_geometry()

    def on_bindings_changed(self, bindings: InputBindings) -> None:
        # Provider may hand over a snapshot taken before dial actions
        # registered — ensure this widget's actions exist on the live registry.
        from ported.lks_utils.gui_qt.widgets.dial_enum_picker_actions import (
            register_defaults,
        )
        register_defaults(bindings)
        self._bindings = bindings

    def on_theme_changed(self, theme: Theme) -> None:
        colors = resolve_dial_enum_picker_colors(theme)
        self._chrome_colors = colors
        self.setStyleSheet("QWidget#dial_enum_picker { background: transparent; border: 0; }")
        self._viewport.setContentsMargins(
            HORIZONTAL_PADDING_PX,
            VERTICAL_PADDING_PX,
            HORIZONTAL_PADDING_PX,
            VERTICAL_PADDING_PX,
        )
        self._viewport.set_colors(
            bg=colors.value_bg,
            hover=colors.value_hover,
            text=colors.text,
        )
        self._stepper.apply_style(text_color=colors.text)
        self._popup.set_text_color(colors.text)
        self._popup.apply_theme_colors(
            colors,
            border_radius_px=self._chrome_border_radius_px,
        )
        if self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST:
            self._sync_shrink_to_largest_geometry()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        paint_dial_enum_chrome(
            painter,
            self.rect(),
            value_rect=self._viewport.geometry(),
            stepper_rect=self._stepper.geometry(),
            colors=self._chrome_colors,
            border_radius_px=self._chrome_border_radius_px,
            value_hovered=self._viewport.is_hovered(),
            stepper_hover=self._stepper.hover_region(),
        )
        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        self.update()

    def showEvent(self, event: QShowEvent) -> None:
        if self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST:
            self._sync_shrink_to_largest_geometry()
        super().showEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if (
            event.type() == QEvent.Type.FontChange
            and self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST
        ):
            self._sync_shrink_to_largest_geometry()
        super().changeEvent(event)

    def sizeHint(self) -> Any:  # type: ignore[override]
        if self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST:
            width, height = shrink_to_largest_size(
                self,
                self._options,
                adornment_px=self._adornment_px,
            )
            return QSize(width, height)
        width = self._fixed_width or 180
        height = self._fixed_height or DEFAULT_ROW_HEIGHT_PX
        return QSize(width, height)

    def minimumSizeHint(self) -> Any:  # type: ignore[override]
        return self.sizeHint()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self._options or not self.isEnabled():
            event.ignore()
            return
        mods, direction = wheel_event_pair(event)
        if self._bindings.matches_wheel(DIAL_ENUM_STEP_NEXT.id, mods, direction):
            self._step(1)
            event.accept()
            return
        if self._bindings.matches_wheel(DIAL_ENUM_STEP_PREV.id, mods, direction):
            self._step(-1)
            event.accept()
            return
        event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._options:
            super().keyPressEvent(event)
            return
        key_text = QKeySequence(event.keyCombination()).toString()
        if self._bindings.matches_key(DIAL_ENUM_STEP_NEXT.id, key_text):
            self._step(1)
            event.accept()
            return
        if self._bindings.matches_key(DIAL_ENUM_STEP_PREV.id, key_text):
            self._step(-1)
            event.accept()
            return
        if self._bindings.matches_key(DIAL_ENUM_OPEN_LIST.id, key_text):
            self._open_popup()
            event.accept()
            return
        super().keyPressEvent(event)

    def _step(self, delta: int) -> None:
        if not self._options:
            return
        count = len(self._options)
        next_index = self._current_index + delta
        if self._wrap:
            next_index %= count
        else:
            next_index = max(0, min(next_index, count - 1))
        if next_index == self._current_index:
            return
        self.set_current_index(next_index, animate=True)

    def _choose_index(self, index: int) -> None:
        self.set_current_index(index, animate=True)

    def _open_popup(self) -> None:
        if not self._options or not self.isEnabled():
            return
        self._popup.populate(
            self._options,
            current_index=self._current_index,
            min_width=self.width(),
        )
        # Defer show so the triggering mouse-release does not instantly dismiss Popup.
        QTimer.singleShot(0, self._deferred_open_popup)

    def _deferred_open_popup(self) -> None:
        if not isValid(self):
            return
        if not self._options or not self.isEnabled() or not self.isVisible():
            return
        self._popup.open_below(self)

    def hideEvent(self, event: QHideEvent) -> None:
        if isValid(self._popup):
            self._popup.dismiss_immediately()
        super().hideEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if isValid(self._popup):
            self._popup.dismiss_immediately()
        super().closeEvent(event)

    def _teardown_popup(self, *_args: object) -> None:
        popup = self._popup
        if popup is None or not isValid(popup):
            return
        popup.dismiss_immediately()
        popup.deleteLater()

    def _refresh_display(self, *, animate: bool, direction: int = 1) -> None:
        if not self._options:
            placeholder = DialEnumOption(value=None, label=EMPTY_LABEL)
            self._viewport.show_option(placeholder, animate=False)
            self.setToolTip("")
            return
        option = self._options[self._current_index]
        self._viewport.show_option(option, animate=animate, direction=direction)
        self.setToolTip(option.label)

    def _refresh_enabled_state(self) -> None:
        enabled = bool(self._options)
        self.setEnabled(enabled)
        self._stepper.set_enabled(enabled)

    def _apply_fixed_geometry(self) -> None:
        if self._size_mode == DialEnumSizeMode.SHRINK_TO_LARGEST:
            self._sync_shrink_to_largest_geometry()
            return
        width = self._fixed_width or 180
        height = self._fixed_height or DEFAULT_ROW_HEIGHT_PX
        self.setFixedSize(width, height)

    def _sync_shrink_to_largest_geometry(self) -> None:
        """Resize to the widest option row once real widget fonts are active."""
        width, height = shrink_to_largest_size(
            self,
            self._options,
            adornment_px=self._adornment_px,
        )
        if QSize(width, height) == self.size():
            return
        self.setFixedSize(width, height)
        self._refresh_display(animate=False)


__all__ = ["QDialEnumPicker"]
