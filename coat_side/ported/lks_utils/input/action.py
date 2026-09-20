"""`Action`: identity for a single user-triggerable command.

Actions are namespaced strings (``"painter.brush.stroke"``) that decouple
*what* the user wants to do from *how* they triggered it. Widgets emit
or consume actions; the `InputBindings` registry maps real events
(``QKeyEvent``, ``QMouseEvent``, ``QWheelEvent``) onto them.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Action:
    """A user-triggerable command identified by a namespaced id.

    Attributes:
        id: Globally unique, dot-namespaced action id. Recommended pattern
            ``"<scope>.<subscope>.<verb>"`` e.g. ``"painter.brush.stroke"``,
            ``"viewport.camera.orbit"``, ``"library.save"``. Lowercase
            ASCII + dots only — used as JSON key in serialised overrides.
        label: Short human-readable name shown in shortcut editors.
        category: Group used to organise the shortcut editor UI
            (e.g. ``"Painter"``, ``"Viewport"``, ``"File"``).
        description: Optional longer description / tooltip text.

    Raises:
        ValueError: If ``id`` is empty or contains characters outside
            ``[a-z0-9._]``.
    """

    id: str
    label: str
    category: str
    description: str = ""
    scope: str = "global"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Action.id cannot be empty")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._")
        bad = set(self.id) - allowed
        if bad:
            raise ValueError(
                f"Action.id may only contain [a-z0-9._], got "
                f"{self.id!r} (bad chars: {sorted(bad)})"
            )


__all__ = ["Action"]
