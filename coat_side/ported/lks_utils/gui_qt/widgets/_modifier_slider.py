"""Internal: QSlider subclass with modifier-key drag UX.

Modifier behaviour during drag:
- **Ctrl**        → snap to 1/N evenly-spaced grid positions
- **Shift**       → fine mode — mouse must travel N× further for the same value change
- **Ctrl+Shift**  → fine movement *and* snap-to-grid
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QWidget

# Number of snap divisions across the full range when Ctrl is held.
_CTRL_SNAP_DIVISIONS: int = 32

# Mouse-travel multiplier for Shift fine mode (slider moves 1/N as fast).
_SHIFT_FINE_DIVISOR: float = 10.0


class _ModifierSlider(QSlider):
    """QSlider with Ctrl / Shift / Ctrl+Shift modifier-key drag UX.

    * **Ctrl** held        → snaps to 1/*N* evenly-spaced grid positions across
      the full range, where *N* is set via :meth:`set_snap_divisions`
      (default 32).
    * **Shift** held       → fine mode: the slider increments at
      1/:attr:`_SHIFT_FINE_DIVISOR` of normal sensitivity.  The anchor
      position is reset whenever Shift transitions from un-held to held so
      that picking up Shift mid-drag never causes a sudden jump.
    * **Ctrl + Shift**     → fine movement constrained to grid snap points.

    Releasing all modifiers restores normal Qt drag behaviour and resets
    the anchor so that any subsequent modifier press starts fresh.
    """

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        """Initialise with default snap divisions."""
        super().__init__(orientation, parent)
        self._snap_divisions: int = _CTRL_SNAP_DIVISIONS
        self._snap_step_int: int = 1
        self._drag_start_x: float = 0.0
        self._drag_start_value: int = 0
        self._shift_was_active: bool = False

    def set_snap_divisions(self, divisions: int) -> None:
        """Set the number of snap increments across the slider range."""
        self._snap_divisions = max(2, divisions)

    def set_snap_step_int(self, step_int: int) -> None:
        """Set the Ctrl-snap step as an integer slider unit count.

        When Ctrl is held, the slider snaps to the nearest multiple of
        *step_int* slider integers from the minimum.  This aligns snap
        positions exactly with the configured ``step`` of the param.
        """
        self._snap_step_int = max(1, step_int)

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def _absolute_value_from_event(self, event: QMouseEvent) -> int:
        """Map cursor position to an absolute slider value."""
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

        lo, hi = self.minimum(), self.maximum()
        if self.orientation() == Qt.Orientation.Horizontal:
            half_h = handle.width() // 2
            slider_min = groove.x() + half_h
            slider_max = groove.right() - half_h
            slider_pos = int(round(event.position().x()))
        else:
            half_h = handle.height() // 2
            slider_min = groove.y() + half_h
            slider_max = groove.bottom() - half_h
            slider_pos = int(round(event.position().y()))

        slider_pos = max(slider_min, min(slider_max, slider_pos))
        span = max(1, slider_max - slider_min)
        return int(
            QStyle.sliderValueFromPosition(
                lo,
                hi,
                slider_pos - slider_min,
                span,
                upsideDown=opt.upsideDown,
            )
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Jump immediately to click position and start drag from that point."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        new_val = self._absolute_value_from_event(event)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            n_steps = round((new_val - self.minimum()) / self._snap_step_int)
            new_val = int(
                max(
                    self.minimum(),
                    min(
                        self.maximum(),
                        self.minimum() + n_steps * self._snap_step_int,
                    ),
                )
            )

        self.setValue(new_val)
        self.setSliderDown(True)
        self.sliderMoved.emit(new_val)

        self._drag_start_x = event.position().x()
        self._drag_start_value = self.value()
        self._shift_was_active = bool(
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Apply Ctrl-snap and/or Shift-fine modifier behaviour during drag."""
        if not self.isSliderDown():
            super().mouseMoveEvent(event)
            return

        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if not ctrl and not shift:
            # No modifiers: map cursor position directly to a value for smooth,
            # continuous tracking.  Calling super() here would use Qt's default
            # page-step-on-groove-click behaviour, which produces snapped
            # interval jumps instead of fluid motion.
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            style = self.style()
            groove = style.subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderGroove, self,
            )
            handle = style.subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderHandle, self,
            )
            half_h = handle.width() // 2
            px_min = groove.x() + half_h
            px_max = groove.right() - half_h
            px_range = px_max - px_min
            if px_range > 0:
                lo, hi = self.minimum(), self.maximum()
                ratio = max(
                    0.0, min(1.0, (event.position().x() - px_min) / px_range))
                self.setValue(int(round(lo + ratio * (hi - lo))))
            # Reset anchor so that a subsequent modifier-press starts from the
            # current cursor position.
            self._drag_start_x = event.position().x()
            self._drag_start_value = self.value()
            self._shift_was_active = False
            return

        # Re-anchor when Shift is newly engaged mid-drag to prevent a jump.
        if shift and not self._shift_was_active:
            self._drag_start_x = event.position().x()
            self._drag_start_value = self.value()
            self._shift_was_active = True
        elif not shift:
            self._shift_was_active = False

        # ── Groove geometry ───────────────────────────────────────────
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self,
        )
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self,
        )
        half_h = handle.width() // 2
        px_min = groove.x() + half_h
        px_max = groove.right() - half_h
        px_range = px_max - px_min
        if px_range <= 0:
            return

        lo, hi = self.minimum(), self.maximum()
        span = hi - lo
        if span == 0:
            return

        if shift:
            # Fine mode: map anchor-relative delta through the fine divisor so
            # the slider moves 1/N as fast as the cursor.
            dx = (event.position().x() - self._drag_start_x) / \
                _SHIFT_FINE_DIVISOR
            start_ratio = (self._drag_start_value - lo) / span
            effective_x = px_min + start_ratio * px_range + dx
            ratio = max(0.0, min(1.0, (effective_x - px_min) / px_range))
            if ctrl:
                # Fine + snap: quantise fine-mode value to the step grid.
                raw_val = lo + ratio * span
                n_steps = round((raw_val - lo) / self._snap_step_int)
                new_val = int(
                    max(lo, min(hi, lo + n_steps * self._snap_step_int)))
            else:
                new_val = int(round(lo + ratio * span))
        else:
            # Ctrl only: absolute cursor → nearest step-aligned grid point.
            ratio = max(
                0.0, min(1.0, (event.position().x() - px_min) / px_range))
            raw_val = lo + ratio * span
            n_steps = round((raw_val - lo) / self._snap_step_int)
            new_val = int(max(lo, min(hi, lo + n_steps * self._snap_step_int)))

        self.setValue(max(lo, min(hi, new_val)))
