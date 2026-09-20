"""Qt ↔ `ported.lks_utils.input` adapter helpers.

Lets a widget extract a `(button, modifiers, gesture)` triple from a
`QMouseEvent` (or modifiers + direction from a `QWheelEvent`) without
hard-coding ``Qt.MouseButton.LeftButton`` / ``Qt.AltModifier`` checks at
every call site.

Kept separate from `binding.py` so the value-object module has zero Qt
dependency and can be unit-tested without a `QApplication`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ported.lks_utils.input.binding import GestureKind, Modifier, MouseButton

if TYPE_CHECKING:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QMouseEvent, QWheelEvent


def qt_button_to_logical(qt_button: "Qt.MouseButton") -> MouseButton | None:
    """Translate a Qt mouse button enum to our `MouseButton`. Returns
    ``None`` for buttons we don't model (extra/forward/back)."""
    from PySide6.QtCore import Qt as _Qt

    if qt_button == _Qt.MouseButton.LeftButton:
        return MouseButton.LEFT
    if qt_button == _Qt.MouseButton.RightButton:
        return MouseButton.RIGHT
    if qt_button == _Qt.MouseButton.MiddleButton:
        return MouseButton.MIDDLE
    return None


def qt_modifiers_to_logical(
    qt_modifiers: "Qt.KeyboardModifier",
) -> frozenset[Modifier]:
    """Translate a Qt modifier mask to our frozenset[Modifier]."""
    from PySide6.QtCore import Qt as _Qt

    out: set[Modifier] = set()
    if qt_modifiers & _Qt.KeyboardModifier.ShiftModifier:
        out.add(Modifier.SHIFT)
    if qt_modifiers & _Qt.KeyboardModifier.ControlModifier:
        out.add(Modifier.CTRL)
    if qt_modifiers & _Qt.KeyboardModifier.AltModifier:
        out.add(Modifier.ALT)
    if qt_modifiers & _Qt.KeyboardModifier.MetaModifier:
        out.add(Modifier.META)
    return frozenset(out)


def mouse_event_triple(
    event: "QMouseEvent", gesture: GestureKind
) -> tuple[MouseButton | None, frozenset[Modifier], GestureKind]:
    """Convenience: extract ``(button, modifiers, gesture)`` from a Qt event.

    Pass ``GestureKind.PRESS`` from `mousePressEvent`, ``GestureKind.DRAG``
    from `mouseMoveEvent` (when buttons are held), ``GestureKind.RELEASE``
    from `mouseReleaseEvent`, etc. Returns ``(None, …)`` when the button
    is one we don't model — the caller should ignore those events.
    """
    button = qt_button_to_logical(event.button())
    if button is None and gesture in (GestureKind.DRAG, GestureKind.RELEASE):
        # During drag/release `event.button()` is NoButton; use the held
        # mask instead — caller resolved which button started the drag.
        from PySide6.QtCore import Qt as _Qt

        for qt_btn, logical in (
            (_Qt.MouseButton.LeftButton, MouseButton.LEFT),
            (_Qt.MouseButton.RightButton, MouseButton.RIGHT),
            (_Qt.MouseButton.MiddleButton, MouseButton.MIDDLE),
        ):
            if event.buttons() & qt_btn:
                button = logical
                break
    return button, qt_modifiers_to_logical(event.modifiers()), gesture


def wheel_event_pair(
    event: "QWheelEvent",
) -> tuple[frozenset[Modifier], str]:
    """Extract ``(modifiers, direction)`` from a `QWheelEvent`.

    ``direction`` is ``"up"`` for a positive vertical delta, ``"down"``
    otherwise.
    """
    direction = "up" if event.angleDelta().y() >= 0 else "down"
    return qt_modifiers_to_logical(event.modifiers()), direction


__all__ = [
    "qt_button_to_logical",
    "qt_modifiers_to_logical",
    "mouse_event_triple",
    "wheel_event_pair",
]
