"""
SculptObject_SetGhost Operator

Unified operator for all ghost-related operations on sculpt objects.
Supports: set ghost, unghost, invert, and isolate (ghost all except).

Uses scope resolution to determine which elements to operate on.
"""
import coat
from enum import Enum
from typing import Callable
from ported.utils.scene_api import SceneAPI
from ported.utils.scope_utils import Scope, resolve_scope
from ported.utils.SceneElement_visibility_utils import (
    set_ghost,
    ghost_elements,
    unghost_elements,
    invert_ghost_on_elements,
    ghost_except,
)
from ported.utils.coat_ui_utils import show_message, show_error


class GhostMode(Enum):
    """Ghost operation mode."""
    SET = "set"          # Set ghost to specific value
    INVERT = "invert"    # Invert current ghost state
    ISOLATE = "isolate"  # Ghost all except scope


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    ghost: bool = True,
    mode: GhostMode = GhostMode.SET,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Apply ghost operation to objects.

    Args:
        scope: Which objects to operate on
        ghost: For SET mode, True = ghost, False = unghost
        mode: Operation mode (SET, INVERT, ISOLATE)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects affected
    """
    from ported.utils.scene_api import SelectionAPI

    # Save selection for restoration (multi-selection aware)
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validate for scope-dependent operations
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    count: int = 0
    total: int = 0

    if mode == GhostMode.ISOLATE:
        # Isolate: ghost all, then unghost only the scope elements
        all_elements: list[coat.SceneElement] = SceneAPI.collect_all_sculpt_objects(
        )
        keep_unghosted: list[coat.SceneElement] = resolve_scope(scope)
        total = len(all_elements)

        # Progress: phase 1 - ghost all
        if progress_callback is not None:
            progress_callback(0, 2, f"Ghosting {len(all_elements)} objects...")

        ghost_count: int = ghost_elements(all_elements)

        # Progress: phase 2 - unghost selection
        if progress_callback is not None:
            progress_callback(1, 2, f"Unghosting {len(keep_unghosted)} objects...")

        unghost_count: int = unghost_elements(keep_unghosted)
        count = ghost_count
        status: str = f"Isolated - ghosted {ghost_count}, unghosted {unghost_count}"

    elif mode == GhostMode.INVERT:
        # Invert: toggle ghost state on scope elements
        elements: list[coat.SceneElement] = resolve_scope(scope)
        total = len(elements)

        if progress_callback is not None:
            for i, el in enumerate(elements):
                progress_callback(i, total, el.name())

        count = invert_ghost_on_elements(elements)
        status = f"Inverted ghost on {count}/{total}"

    else:  # GhostMode.SET
        elements = resolve_scope(scope)
        total = len(elements)
        action: str = "ghosted" if ghost else "unghosted"

        if progress_callback is not None:
            for i, el in enumerate(elements):
                progress_callback(i, total, f"{action.capitalize()} {el.name()}")

        count = set_ghost(elements, ghost)
        status = f"{action.capitalize()} {count}/{total}"

    # Restore selection (multi-selection aware)
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    show_message(f"{status} objects", 2000)
    return count
