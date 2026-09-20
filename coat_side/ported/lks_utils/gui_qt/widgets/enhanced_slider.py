"""QEnhancedSlider — gestural numerical slider with modifier keys, soft overflow, and log mode.

Layout::

    [========slider========] [value_spinbox]

Linear mode: normal slider behaviour.
Logarithmic mode: slider controls log(value); powers-of-10 tick labels are
painted below the groove inside the slider's own paint area.
"""
from __future__ import annotations

import math
import sys

# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import Qt, Signal, QRect, QSize
from PySide6.QtGui import (
    QColor, QMouseEvent, QPainter, QPen, QFont, QPaintEvent,
)
from PySide6.QtWidgets import (
    QDoubleSpinBox, QHBoxLayout, QSizePolicy, QStyle,
    QStyleOptionSlider, QWidget,
)

from ported.lks_utils.gui_qt.widgets._modifier_slider import _ModifierSlider

# ── Constants ────────────────────────────────────────────────────────────────

_CTRL_SNAP_DIVISIONS: int = 32
_SHIFT_FINE_DIVISOR: float = 10.0
_LOG_INTERNAL_RANGE: int = 10_000  # slider integer positions for log mode
_TICK_LABEL_HEIGHT: int = 14       # vertical space at bottom of slider for tick labels


def _decimals_from_step(step: float) -> int:
    """Infer decimal places from a step value."""
    if step <= 0:
        return 2
    return max(0, -int(math.floor(math.log10(step))))


def _format_tick_label(value: float) -> str:
    """Format a tick value as a compact label (1, 10, 100, 1k, 10k, 100k, 1M, 1B)."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.0f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}k"
    if value >= 1:
        return f"{value:.0f}"
    return f"{value:.{_decimals_from_step(max(value, 1e-9))}f}"


# ═══════════════════════════════════════════════════════════════════════════════
# Internal slider bar — extends _ModifierSlider with soft overflow + log
# ═══════════════════════════════════════════════════════════════════════════════

class _EnhancedSliderBar(_ModifierSlider):
    """Internal QSlider with soft-overflow and logarithmic-mode support.

    Soft overflow
    -------------
    When ``hard_min`` / ``hard_max`` are set, dragging past either edge of the
    groove pins the handle visually but continues to change the logical float
    value (capped at the hard limit).

    Logarithmic mode
    ----------------
    The slider integer range maps to ``log10(value)`` linearly.  Ctrl-snap
    snaps to the nearest power-of-10 tick.  Shift-fine works in log space.

    Tick labels are painted below the groove in this widget's own
    ``paintEvent`` — no external overlay widget needed.
    """

    # Signal emitted with the *logical* float value (may exceed visible range).
    float_value_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._min_value: float = 0.0
        self._max_value: float = 1.0
        self._hard_min: float | None = None
        self._hard_max: float | None = None
        self._step: float = 0.01
        self._scale: int = 1
        self._float_value: float = 0.5
        self._logarithmic: bool = False
        self._log_min: float = 0.0
        self._log_max: float = 1.0
        self._overflow_below: bool = False
        self._overflow_above: bool = False
        self._blocked: bool = False

        # Cached tick info for painting
        self._tick_labels: list[tuple[str, float]] = []  # (label, ratio 0..1)
        self._tick_values: list[float] = []               # snap targets in log mode
        self._log_bottom_margin: int = 0                  # px reserved for tick labels

        self.setMouseTracking(True)

    # ── Configuration ────────────────────────────────────────────────────────

    def configure(
        self,
        min_value: float,
        max_value: float,
        default_value: float,
        step: float,
        scale: int,
        hard_min: float | None,
        hard_max: float | None,
        logarithmic: bool,
    ) -> None:
        """Apply all configuration at once (called once after construction)."""
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._scale = scale
        self._hard_min = hard_min
        self._hard_max = hard_max
        self._logarithmic = logarithmic
        self._float_value = default_value
        self._log_bottom_margin = _TICK_LABEL_HEIGHT if logarithmic else 0

        if logarithmic:
            raw_min: float = max(min_value, 1e-30)
            raw_max: float = max(max_value, raw_min * 10)
            self._log_min = math.log10(raw_min)
            self._log_max = math.log10(raw_max)
            self.setRange(0, _LOG_INTERNAL_RANGE)
            self.set_snap_step_int(max(1, _LOG_INTERNAL_RANGE // _CTRL_SNAP_DIVISIONS))
            self._build_log_ticks()
            self._update_slider_int()
            # Reserve bottom space for tick labels via stylesheet
            self.setStyleSheet(
                "QSlider::groove:horizontal { margin-bottom: " + str(_TICK_LABEL_HEIGHT) + "px; }"
            )
        else:
            int_min: int = round(min_value * scale)
            int_max: int = round(max_value * scale)
            self.setRange(int_min, int_max)
            snap_step_int = max(1, round(step * scale))
            self.set_snap_step_int(snap_step_int)
            self._update_slider_int()
            self.setStyleSheet("")

    # ── Log tick computation ─────────────────────────────────────────────────

    def _build_log_ticks(self) -> None:
        """Compute tick labels and positions for log mode."""
        self._tick_labels.clear()
        self._tick_values.clear()

        lo_exp: int = int(math.floor(self._log_min))
        hi_exp: int = int(math.ceil(self._log_max))
        log_span: float = self._log_max - self._log_min

        for exp in range(lo_exp, hi_exp + 1):
            val: float = 10.0 ** exp
            if val < self._min_value * 0.5 or val > self._max_value * 2.0:
                continue
            ratio: float = (exp - self._log_min) / log_span if log_span > 0 else 0.0
            if 0.0 <= ratio <= 1.0:
                self._tick_labels.append((_format_tick_label(val), ratio))
                self._tick_values.append(val)

    # ── Float ↔ int conversion ──────────────────────────────────────────────

    def _float_to_int(self, value: float) -> int:
        """Map float value → slider integer, clamped to visible range."""
        if self._logarithmic:
            v: float = max(value, 1e-30)
            ratio: float = (
                (math.log10(v) - self._log_min) / (self._log_max - self._log_min)
            )
            ratio = max(0.0, min(1.0, ratio))
            return round(ratio * _LOG_INTERNAL_RANGE)
        if self._scale <= 0:
            return 0
        raw: int = round(value * self._scale)
        return max(self.minimum(), min(self.maximum(), raw))

    def _int_to_float(self, int_val: int) -> float:
        """Map slider integer → float value."""
        if self._logarithmic:
            ratio: float = int_val / _LOG_INTERNAL_RANGE
            log_val: float = self._log_min + ratio * (self._log_max - self._log_min)
            return 10.0 ** log_val
        return int_val / self._scale if self._scale > 0 else float(int_val)

    def _clamp_value(self, value: float) -> float:
        """Clamp *value* to hard limits if set."""
        if self._hard_min is not None and value < self._hard_min:
            return self._hard_min
        if self._hard_max is not None and value > self._hard_max:
            return self._hard_max
        return value

    # ── Public value access ──────────────────────────────────────────────────

    def float_value(self) -> float:
        """Return the current logical float value."""
        return self._float_value

    def set_float_value(self, value: float) -> None:
        """Programmatically set the float value without overflow tracking."""
        self._float_value = self._clamp_value(value)
        self._blocked = True
        self._update_slider_int()
        self._blocked = False
        self._update_overflow_state()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _update_slider_int(self) -> None:
        """Set the QSlider integer position from _float_value (clamped to visible range)."""
        int_val: int = self._float_to_int(self._float_value)
        self.setValue(int_val)

    def _update_overflow_state(self) -> None:
        """Update visual overflow indicators."""
        was_below: bool = self._overflow_below
        was_above: bool = self._overflow_above
        self._overflow_below = (
            self._hard_min is not None and self._float_value < self._min_value
        )
        self._overflow_above = (
            self._hard_max is not None and self._float_value > self._max_value
        )
        if was_below != self._overflow_below or was_above != self._overflow_above:
            self.update()

    # ── Modifier-key snap in log mode ────────────────────────────────────────

    def _snap_log_value(self, value: float) -> float:
        """Snap *value* to the nearest power-of-10 tick in log mode."""
        if not self._tick_values:
            return value
        best: float = self._tick_values[0]
        best_dist: float = abs(math.log10(max(value, 1e-30)) - math.log10(best))
        for tv in self._tick_values[1:]:
            dist: float = abs(math.log10(max(value, 1e-30)) - math.log10(tv))
            if dist < best_dist:
                best_dist = dist
                best = tv
        return best

    # ── Groove geometry helper ───────────────────────────────────────────────

    def _groove_geometry(self) -> tuple[float, float, float, float]:
        """Return (px_min, px_max, px_range, half_handle)."""
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        half_h: int = handle.width() // 2
        px_min: float = float(groove.x() + half_h)
        px_max: float = float(groove.right() - half_h)
        px_range: float = px_max - px_min
        return px_min, px_max, px_range, float(half_h)

    def _cursor_to_float(self, cursor_x: float, px_min: float, px_range: float) -> float:
        """Map cursor X position to a float value (unclamped)."""
        if px_range <= 0:
            return self._float_value
        ratio: float = (cursor_x - px_min) / px_range
        if self._logarithmic:
            log_val: float = self._log_min + ratio * (self._log_max - self._log_min)
            return 10.0 ** log_val
        return self._min_value + ratio * (self._max_value - self._min_value)

    # ── Mouse events (soft overflow) ─────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Jump to click position; handle overflow and modifiers."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        px_min, px_max, px_range, _ = self._groove_geometry()
        cursor_x: float = event.position().x()
        raw_val: float = self._cursor_to_float(cursor_x, px_min, px_range)

        ctrl: bool = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if ctrl:
            if self._logarithmic:
                raw_val = self._snap_log_value(raw_val)
            else:
                n_steps: int = round(
                    (raw_val - self._min_value) / self._step
                )
                raw_val = self._min_value + n_steps * self._step

        self._float_value = self._clamp_value(raw_val)
        self._blocked = True
        self._update_slider_int()
        self._blocked = False
        self._update_overflow_state()

        self.setSliderDown(True)
        self.sliderMoved.emit(self.value())
        self.float_value_changed.emit(self._float_value)

        self._drag_start_x = cursor_x
        self._drag_start_value = self._float_value
        self._shift_was_active = bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Apply modifiers and soft overflow during drag."""
        if not self.isSliderDown():
            super().mouseMoveEvent(event)
            return

        px_min, px_max, px_range, _ = self._groove_geometry()
        cursor_x: float = event.position().x()
        ctrl: bool = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift: bool = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if not ctrl and not shift:
            if px_range > 0:
                new_val: float = self._cursor_to_float(cursor_x, px_min, px_range)
            else:
                new_val = self._float_value
            self._float_value = self._clamp_value(new_val)
            self._blocked = True
            self._update_slider_int()
            self._blocked = False
            self._update_overflow_state()
            self.float_value_changed.emit(self._float_value)

            self._drag_start_x = cursor_x
            self._drag_start_value = self._float_value
            self._shift_was_active = False
            return

        if shift and not self._shift_was_active:
            self._drag_start_x = cursor_x
            self._drag_start_value = self._float_value
            self._shift_was_active = True
        elif not shift:
            self._shift_was_active = False

        if px_range <= 0:
            return

        raw_val: float = self._cursor_to_float(cursor_x, px_min, px_range)

        if shift:
            dx: float = (cursor_x - self._drag_start_x) / _SHIFT_FINE_DIVISOR
            if self._logarithmic:
                start_log: float = math.log10(max(self._drag_start_value, 1e-30))
                start_ratio: float = (
                    (start_log - self._log_min) / (self._log_max - self._log_min)
                )
            else:
                start_ratio = (
                    (self._drag_start_value - self._min_value)
                    / max(self._max_value - self._min_value, 1e-30)
                )
            effective_x: float = px_min + start_ratio * px_range + dx
            raw_val = self._cursor_to_float(effective_x, px_min, px_range)

        if ctrl:
            if self._logarithmic:
                raw_val = self._snap_log_value(raw_val)
            else:
                n_steps = round((raw_val - self._min_value) / self._step)
                raw_val = self._min_value + n_steps * self._step

        self._float_value = self._clamp_value(raw_val)
        self._blocked = True
        self._update_slider_int()
        self._blocked = False
        self._update_overflow_state()
        self.float_value_changed.emit(self._float_value)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Clear drag state on mouse release so the slider stops tracking."""
        self.setSliderDown(False)
        super().mouseReleaseEvent(event)

    # ── Paint — tick labels painted below the groove ─────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """Paint slider normally, then draw tick labels below the groove."""
        super().paintEvent(event)

        if not self._logarithmic or not self._tick_labels:
            return

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        half_h: int = handle.width() // 2
        px_min: float = float(groove.x() + half_h)
        px_max: float = float(groove.right() - half_h)
        px_range: float = px_max - px_min
        if px_range <= 0:
            return

        # Paint labels just below the groove, inside the bottom margin
        label_y: int = groove.bottom() + 2
        label_height: int = self.height() - label_y

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Consolas", 7)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#777777")))

        for label, ratio in self._tick_labels:
            x: float = px_min + ratio * px_range
            text_width: float = float(painter.fontMetrics().horizontalAdvance(label))
            painter.drawText(
                QRect(int(x - text_width / 2), label_y, int(text_width), label_height),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# Public widget
# ═══════════════════════════════════════════════════════════════════════════════

class QEnhancedSlider(QWidget):
    """Gestural numerical slider with modifier-key behaviour, editable spinbox,
    soft overflow, and optional logarithmic mode.

    Layout::

        [========slider========] [value_spinbox]

    The slider sits inline at text-line height.  In logarithmic mode tick
    labels are painted inside the slider's own bottom margin — no extra
    vertical space is consumed by an external overlay widget.

    Linear mode
    -----------
    Normal slider behaviour.  The slider range maps linearly to the value.

    Logarithmic mode
    ----------------
    The slider controls ``log10(value)``.  Tick labels showing powers of 10 are
    painted below the groove.  Ctrl-snap snaps to the nearest labeled tick.

    Modifier keys during drag
    -------------------------
    * No modifier  — smooth continuous tracking
    * **Ctrl**     — snap to step grid (linear) or nearest tick (log)
    * **Shift**    — fine-tune at 1/10 sensitivity
    * **Ctrl+Shift** — fine-tune constrained to step grid

    Soft overflow
    -------------
    When ``hard_min`` / ``hard_max`` are set, dragging past either edge of the
    groove pins the handle visually but continues to change the logical value
    (capped at the hard limit).  The spinbox shows the unclamped value.

    Signals:
        value_changed(float): Emitted whenever the value changes.

    Args:
        min_value: Display minimum of the slider groove.
        max_value: Display maximum of the slider groove.
        default_value: Initial value.
        step: Base step increment for Ctrl-snap in linear mode.
        decimals: Decimal places in the spinbox.  Inferred from *step* when None.
        hard_min: Absolute floor (None disables soft overflow below).
        hard_max: Absolute ceiling (None disables soft overflow above).
        spinbox_width: Fixed width of the spinbox (px).
        logarithmic: Enable log mode.
        parent: Parent widget.
    """

    value_changed = Signal(float)

    def __init__(
        self,
        *,
        min_value: float = 0.0,
        max_value: float = 1.0,
        default_value: float = 0.5,
        step: float = 0.01,
        decimals: int | None = None,
        hard_min: float | None = None,
        hard_max: float | None = None,
        spinbox_width: int = 72,
        logarithmic: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._step: float = step
        self._decimals: int = (
            decimals if decimals is not None else _decimals_from_step(step)
        )
        self._min_value: float = min_value
        self._max_value: float = max_value
        self._hard_min: float | None = hard_min
        self._hard_max: float | None = hard_max
        self._logarithmic: bool = logarithmic
        self._blocked: bool = False

        # ── Compute scale for integer slider precision ───────────────────────
        range_span: float = max(abs(max_value - min_value), 1e-30)
        target_positions: int = 10_000
        self._scale: int = max(1, int(target_positions / range_span))
        min_scale_for_snap: int = max(1, int(1.0 / max(step, 1e-30)))
        self._scale = max(self._scale, min_scale_for_snap)
        max_scale_for_range: int = int(500_000_000 / range_span) if range_span > 0 else 1
        self._scale = min(self._scale, max(1, max_scale_for_range))

        # ── Outer layout: slider + spinbox inline ────────────────────────────
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(6)

        self._slider = _EnhancedSliderBar()
        self._slider.configure(
            min_value=min_value,
            max_value=max_value,
            default_value=default_value,
            step=step,
            scale=self._scale,
            hard_min=hard_min,
            hard_max=hard_max,
            logarithmic=logarithmic,
        )
        self._slider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._slider.float_value_changed.connect(self._on_slider_float_changed)
        h_layout.addWidget(self._slider, stretch=1)

        # ── Spinbox ──────────────────────────────────────────────────────────
        sb_min: float = hard_min if hard_min is not None else min_value
        sb_max: float = hard_max if hard_max is not None else max_value
        self._spinbox = QDoubleSpinBox()
        self._spinbox.setRange(sb_min, sb_max)
        self._spinbox.setValue(default_value)
        self._spinbox.setSingleStep(step)
        self._spinbox.setDecimals(self._decimals)
        self._spinbox.setFixedWidth(spinbox_width)
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)
        h_layout.addWidget(self._spinbox)

        self._apply_overflow_style(False)

    # ── Stylesheet helpers ───────────────────────────────────────────────────

    def _apply_overflow_style(self, overflow: bool) -> None:
        """Apply a subtle visual distinction when the value is in overflow."""
        if overflow:
            base = (
                "QSlider::handle:horizontal {"
                "  background: #ff8a65;"
                "  border: 1px solid #ff7043;"
                "  border-radius: 6px;"
                "}"
            )
            if self._logarithmic:
                base += (
                    "QSlider::groove:horizontal { margin-bottom: "
                    + str(_TICK_LABEL_HEIGHT) + "px; }"
                )
            self._slider.setStyleSheet(base)
        else:
            if self._logarithmic:
                self._slider.setStyleSheet(
                    "QSlider::groove:horizontal { margin-bottom: "
                    + str(_TICK_LABEL_HEIGHT) + "px; }"
                )
            else:
                self._slider.setStyleSheet("")

    # ── Public API ───────────────────────────────────────────────────────────

    def value(self) -> float:
        """Return the current float value."""
        return self._slider.float_value()

    def setValue(self, value: float) -> None:
        """Set the value programmatically (no signal emission)."""
        self._blocked = True
        self._slider.set_float_value(value)
        self._spinbox.setValue(value)
        self._blocked = False

    # ── Signal handlers ──────────────────────────────────────────────────────

    def _on_slider_float_changed(self, value: float) -> None:
        """Slider moved — sync spinbox and emit."""
        if self._blocked:
            return
        self._blocked = True
        self._spinbox.setValue(value)
        self._blocked = False
        overflow: bool = (
            (self._hard_min is not None and value < self._min_value)
            or (self._hard_max is not None and value > self._max_value)
        )
        self._apply_overflow_style(overflow)
        self.value_changed.emit(value)

    def _on_spinbox_changed(self, value: float) -> None:
        """Spinbox edited — sync slider and emit."""
        if self._blocked:
            return
        self._blocked = True
        self._slider.set_float_value(value)
        self._blocked = False
        self.value_changed.emit(value)
