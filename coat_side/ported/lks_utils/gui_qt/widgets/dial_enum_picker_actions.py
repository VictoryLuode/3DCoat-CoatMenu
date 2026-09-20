"""Input actions for QDialEnumPicker."""
from __future__ import annotations

from ported.lks_utils.input import (
    Action,
    Binding,
    InputBindings,
    KeyBinding,
    WheelBinding,
    get_default_bindings,
)

DIAL_ENUM_STEP_PREV = Action(
    id="gui_qt.dial_enum_picker.step_prev",
    label="Previous option",
    category="GUI",
    description="Step to the previous dial enum option.",
    scope="gui_qt.widgets",
)
DIAL_ENUM_STEP_NEXT = Action(
    id="gui_qt.dial_enum_picker.step_next",
    label="Next option",
    category="GUI",
    description="Step to the next dial enum option.",
    scope="gui_qt.widgets",
)
DIAL_ENUM_OPEN_LIST = Action(
    id="gui_qt.dial_enum_picker.open_list",
    label="Open option list",
    category="GUI",
    description="Open the full option list popup.",
    scope="gui_qt.widgets",
)

DEFAULT_BINDINGS: list[tuple[Action, list[Binding]]] = [
    (
        DIAL_ENUM_STEP_PREV,
        [WheelBinding(direction="up"), KeyBinding("Up")],
    ),
    (
        DIAL_ENUM_STEP_NEXT,
        [WheelBinding(direction="down"), KeyBinding("Down")],
    ),
    (
        DIAL_ENUM_OPEN_LIST,
        [KeyBinding("Return"), KeyBinding("Space")],
    ),
]


def register_defaults(bindings: InputBindings) -> None:
    """Register default dial enum picker bindings."""
    for action, binding_list in DEFAULT_BINDINGS:
        bindings.register(action, binding_list)


register_defaults(get_default_bindings())


__all__ = [
    "DIAL_ENUM_OPEN_LIST",
    "DIAL_ENUM_STEP_NEXT",
    "DIAL_ENUM_STEP_PREV",
    "DEFAULT_BINDINGS",
    "register_defaults",
]
