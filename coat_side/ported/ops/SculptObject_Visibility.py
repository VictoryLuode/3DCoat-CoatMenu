"""
SculptObject_Visibility Operator

Toggle visibility (hide/show) on sculpt objects.
Note: This is different from ghost - visibility completely hides the object.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from enum import Enum
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope
from ported.utils.SceneElement_visibility_utils import (
    set_visibility,
    hide_elements,
    show_elements,
    invert_visibility_on_elements,
    hide_except,
)
from ported.utils.coat_ui_utils import show_message, show_error


class VisibilityMode(Enum):
    """Visibility operation mode."""
    SET = "set"          # Set visibility to specific value
    INVERT = "invert"    # Invert current visibility state
    ISOLATE = "isolate"  # Hide all except scope


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    visible: bool = True,
    mode: VisibilityMode = VisibilityMode.SET,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Apply visibility operation to objects.

    Args:
        scope: Which objects to operate on
        visible: For SET mode, True = show, False = hide
        mode: Operation mode (SET, INVERT, ISOLATE)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects affected
    """
    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validation for scope check should use a separate variable
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Resolve elements - use include_hidden=True for visibility ported.ops
    # so we can show hidden elements
    elements: list[coat.SceneElement] = resolve_scope(
        scope, include_hidden=True)

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    count: int = 0

    if mode == VisibilityMode.INVERT:
        # Invert visibility on scope elements
        total: int = len(elements)
        if progress_callback is not None:
            for i, el in enumerate(elements):
                progress_callback(i, total, el.name())
        count = invert_visibility_on_elements(elements)
        status: str = f"Inverted visibility on {count}"

    elif mode == VisibilityMode.ISOLATE:
        # Hide all except scope elements
        all_elements: list[coat.SceneElement] = SceneAPI.collect_all_sculpt_objects(
        )
        count = hide_except(all_elements, elements)
        status = f"Isolated {len(elements)}, hid {count}"

    else:  # SET mode
        if visible:
            total = len(elements)
            if progress_callback is not None:
                for i, el in enumerate(elements):
                    progress_callback(i, total, el.name())
            count = show_elements(elements)
            status = f"Showed {count}"
        else:
            total = len(elements)
            if progress_callback is not None:
                for i, el in enumerate(elements):
                    progress_callback(i, total, el.name())
            count = hide_elements(elements)
            status = f"Hid {count}"

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    show_message(f"{status} objects", 2000)
    return count
