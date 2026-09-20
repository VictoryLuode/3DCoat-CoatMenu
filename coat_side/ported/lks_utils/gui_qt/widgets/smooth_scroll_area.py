"""
Smooth-scrolling QScrollArea with snappy lerp animation.

QSmoothScrollArea extends QScrollArea by adding momentum-based smooth
scrolling via QPropertyAnimation.  Wheel events set an immediate target
position, and the visual scroll position lerps toward it with an
ease-out curve.

Usage::

    scroll = QSmoothScrollArea()
    scroll.setWidget(my_content_widget)
    scroll.animation_duration = 120  # snappier
    scroll.easing_curve = QEasingCurve(QEasingCurve.Type.OutQuad)
"""
from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QScrollArea, QScrollBar


class QSmoothScrollArea(QScrollArea):
    """QScrollArea with smooth, animated scrolling.

    Wheel and trackpad events update an internal target scroll position.
    A ``QPropertyAnimation`` interpolates the visual scroll toward the
    target using an ease-out curve, producing a snappy deceleration
    effect.  Each new wheel event restarts the animation from the
    current visual position, so rapid scrolling feels continuous.

    Configurable Properties:
        *animation_duration* (int) — Duration in ms (default 150).
        *easing_curve* (QEasingCurve) — Easing type (default OutCubic).
        *smooth_scrolling_enabled* (bool) — Toggle animation (default True).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._animation_duration: int = 150
        self._easing_curve: QEasingCurve = QEasingCurve(
            QEasingCurve.Type.OutCubic)
        self._smooth_scrolling_enabled: bool = True

        # Active animations — one per axis
        self._anim_v: QPropertyAnimation | None = None
        self._anim_h: QPropertyAnimation | None = None

    # ── Configurable Properties ──────────────────────────────────────────

    @property
    def animation_duration(self) -> int:
        """Duration of the scroll animation in milliseconds (default 150)."""
        return self._animation_duration

    @animation_duration.setter
    def animation_duration(self, value: int) -> None:
        self._animation_duration = max(1, value)

    @property
    def easing_curve(self) -> QEasingCurve:
        """Easing curve for the scroll animation (default OutCubic)."""
        return self._easing_curve

    @easing_curve.setter
    def easing_curve(self, value: QEasingCurve) -> None:
        self._easing_curve = value

    @property
    def smooth_scrolling_enabled(self) -> bool:
        """Whether smooth scrolling animation is enabled (default True)."""
        return self._smooth_scrolling_enabled

    @smooth_scrolling_enabled.setter
    def smooth_scrolling_enabled(self, value: bool) -> None:
        self._smooth_scrolling_enabled = value

    # ── Wheel Event ──────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Capture wheel/trackpad events and animate toward the new target.

        Falls back to native scrolling when ``smooth_scrolling_enabled``
        is ``False``.  Prefers ``pixelDelta()`` for high-precision
        trackpads, falling back to ``angleDelta()`` for mouse wheels.
        """
        if not self._smooth_scrolling_enabled:
            super().wheelEvent(event)
            return

        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()

        # Prefer pixel delta (trackpad precision); fall back to angle delta
        dy: float = (
            float(pixel_delta.y())
            if pixel_delta.y() != 0
            else float(angle_delta.y())
        )
        dx: float = (
            float(pixel_delta.x())
            if pixel_delta.x() != 0
            else float(angle_delta.x())
        )

        # Vertical scroll
        vb: QScrollBar = self.verticalScrollBar()
        if vb and vb.isVisible() and abs(dy) > 0.1:
            current: int = vb.value()
            target: int = current - int(round(dy))
            target = max(vb.minimum(), min(target, vb.maximum()))
            self._animate_to(vb, target, is_vertical=True)

        # Horizontal scroll (Shift+wheel or trackpad swipe)
        hb: QScrollBar = self.horizontalScrollBar()
        if hb and hb.isVisible() and abs(dx) > 0.1:
            current: int = hb.value()
            target: int = current - int(round(dx))
            target = max(hb.minimum(), min(target, hb.maximum()))
            self._animate_to(hb, target, is_vertical=False)

        event.accept()

    # ── Animation ────────────────────────────────────────────────────────

    def _animate_to(
        self, sb: QScrollBar, target: int, *, is_vertical: bool
    ) -> None:
        """Start or restart a smooth scroll animation for *sb* toward *target*.

        Stops any running animation on this axis, reads the scrollbar's
        current visual position, and starts a fresh animation from that
        position to *target* using the configured duration and easing
        curve.
        """
        # Stop the running animation for this axis
        anim: QPropertyAnimation | None = (
            self._anim_v if is_vertical else self._anim_h
        )
        if anim is not None and anim.state() == QAbstractAnimation.State.Running:
            anim.stop()

        # New animation from current visual position to target
        anim = QPropertyAnimation(sb, b"value")
        anim.setDuration(self._animation_duration)
        anim.setEasingCurve(self._easing_curve)
        anim.setStartValue(sb.value())
        anim.setEndValue(target)
        anim.start()

        if is_vertical:
            self._anim_v = anim
        else:
            self._anim_h = anim


__all__ = ["QSmoothScrollArea"]
