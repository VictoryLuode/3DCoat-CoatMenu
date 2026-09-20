"""
SculptObject_LiveBool Operator

Set the live boolean mode on existing sculpt objects.

Unlike SculptObject_NewVoxBool (which clones and creates child objects),
this operator simply sets the live boolean mode flag *on the selected element
itself*. Use this when you already have an object placed inside a parent's
subtree and want to assign or change its boolean role.

BooleanMode.NONE turns live booleans off for the element.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.SceneElement_boolean_utils import (
    BooleanMode,
    set_live_boolean_mode_on_elements,
)
from ported.utils.coat_ui_utils import show_message, show_error

# Re-export BooleanMode so callers can import from here
__all__ = ["main", "BooleanMode"]


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    mode: BooleanMode = BooleanMode.SUBTRACT,
    scope: Scope = Scope.CURRENT,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Set the live boolean mode on selected sculpt objects.

    Args:
        mode: The boolean mode to assign (NONE / SUBTRACT / INTERSECT / UNION)
        scope: Which elements to operate on
        preserve_selection: Whether to restore selection after the operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of elements that were updated
    """
    # Validate that something is selected when needed
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Save selection before iterating
    saved: list[coat.SceneElement] = []
    if preserve_selection:
        saved = SelectionAPI.save_selection()

    # Resolve target elements
    elements, _ = resolve_scope_skip_instances(scope)
    if not elements:
        show_error("No objects to process", 2000)
        return 0

    # Apply mode to all resolved elements
    count: int = set_live_boolean_mode_on_elements(
        elements, mode, progress_callback=progress_callback
    )

    # Restore selection
    if preserve_selection and saved:
        SelectionAPI.restore_selection(saved)

    # Feedback
    mode_label: str = mode.name.capitalize()
    if count:
        show_message(f"Live bool → {mode_label} on {count} object(s)", 2000)
    else:
        show_error("No sculpt objects found in scope", 2000)

    return count


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def set_union(scope: Scope = Scope.CURRENT) -> int:
    """Set live boolean mode to UNION."""
    return main(mode=BooleanMode.UNION, scope=scope)


def set_subtract(scope: Scope = Scope.CURRENT) -> int:
    """Set live boolean mode to SUBTRACT."""
    return main(mode=BooleanMode.SUBTRACT, scope=scope)


def set_intersect(scope: Scope = Scope.CURRENT) -> int:
    """Set live boolean mode to INTERSECT."""
    return main(mode=BooleanMode.INTERSECT, scope=scope)


def set_none(scope: Scope = Scope.CURRENT) -> int:
    """Turn off live booleans (set mode to NONE)."""
    return main(mode=BooleanMode.NONE, scope=scope)
