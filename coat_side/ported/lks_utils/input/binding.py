"""Binding value objects.

A `Binding` is one trigger that fires an `Action`. Subtypes:

* `KeyBinding`  — keyboard shortcut (``Ctrl+S``, ``Shift+F2``).
* `MouseBinding` — mouse button + modifiers + gesture kind
  (``LMB drag``, ``Shift+RMB drag``, ``Alt+MMB click``).
* `WheelBinding` — scroll wheel + modifiers (``wheel``, ``Ctrl+wheel``).

Bindings are intentionally GUI-toolkit-agnostic value objects. The
adapter layer (``ported.lks_utils.input.qt_adapter``) translates them to/from
``QKeyEvent`` / ``QMouseEvent`` / ``QWheelEvent``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class MouseButton(str, Enum):
    """Logical mouse button identifiers (toolkit-agnostic)."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class Modifier(str, Enum):
    """Keyboard modifier identifiers (toolkit-agnostic)."""

    SHIFT = "shift"
    CTRL = "ctrl"
    ALT = "alt"
    META = "meta"  # Cmd on macOS, Win on Windows


class GestureKind(str, Enum):
    """Mouse gesture kind for `MouseBinding`."""

    PRESS = "press"          # button down (one-shot)
    RELEASE = "release"      # button up
    CLICK = "click"          # press + release without significant motion
    DOUBLE_CLICK = "double_click"
    DRAG = "drag"            # press → motion → release stream


@dataclass(frozen=True, slots=True)
class KeyBinding:
    """A keyboard shortcut.

    Attributes:
        key: Qt key sequence string (e.g. ``"Ctrl+S"``, ``"Shift+F2"``).
            Use the standard Qt ``QKeySequence`` format so we can hand it
            straight to ``QShortcut`` / ``QAction``.
    """

    key: str


@dataclass(frozen=True, slots=True)
class MouseBinding:
    """A mouse gesture.

    Attributes:
        button: Which mouse button fires this binding.
        modifiers: Frozenset of modifiers that must be held. Order does
            not matter; an empty frozenset means "no modifiers".
        gesture: Which gesture kind triggers the binding (press, drag,
            click, double-click, release).
    """

    button: MouseButton
    modifiers: frozenset[Modifier] = field(default_factory=frozenset)
    gesture: GestureKind = GestureKind.PRESS


@dataclass(frozen=True, slots=True)
class WheelBinding:
    """A scroll-wheel gesture.

    Attributes:
        modifiers: Modifiers that must be held (empty = bare wheel).
        direction: ``"any"`` matches scroll up or down. ``"up"`` /
            ``"down"`` match only one direction (useful for "Ctrl+wheel
            up = zoom in").
    """

    modifiers: frozenset[Modifier] = field(default_factory=frozenset)
    direction: str = "any"  # "any" | "up" | "down"

    def __post_init__(self) -> None:
        if self.direction not in {"any", "up", "down"}:
            raise ValueError(
                f"WheelBinding.direction must be 'any'|'up'|'down', got "
                f"{self.direction!r}"
            )


# Discriminated union of binding kinds. Use `isinstance` to dispatch.
Binding = Union[KeyBinding, MouseBinding, WheelBinding]


__all__ = [
    "MouseButton",
    "Modifier",
    "GestureKind",
    "KeyBinding",
    "MouseBinding",
    "WheelBinding",
    "Binding",
]
