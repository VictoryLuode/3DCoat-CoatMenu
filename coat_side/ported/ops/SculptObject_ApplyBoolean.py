"""
SculptObject_ApplyBoolean Operator

Apply (collapse) the live-boolean subtree of selected sculpt object(s).

Two modes:
- keep_original=False : collapse the boolean tree on each selected element
  in place. The element's `_Subtract|_Intersect|_Union` suffix (if any) is
  stripped after collapse since it is no longer a boolean child.
- keep_original=True  : duplicate each selected element, hide the original,
  collapse the boolean tree on the duplicate. Original is preserved as a
  hidden, editable backup.

Uses scope resolution to determine which elements to operate on
(typically `Scope.CURRENT`).
"""
import coat
from typing import Callable

from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.SceneElement_boolean_utils import (
    collapse_boolean_tree,
    collapse_boolean_tree_keep_original,
)
from ported.utils.coat_ui_utils import show_message, show_error


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    keep_original: bool = False,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Apply (collapse) live-boolean subtrees on scoped sculpt objects.

    Args:
        scope: Which elements to apply on
        keep_original: If True, duplicate each element and collapse the
            duplicate while hiding the original.
        preserve_selection: Whether to restore selection after the operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of elements processed
    """
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    saved: list[coat.SceneElement] = []
    if preserve_selection:
        saved = SelectionAPI.save_selection()

    elements, _ = resolve_scope_skip_instances(scope)
    if not elements:
        show_error("No objects to process", 2000)
        return 0

    total: int = len(elements)

    count: int = 0
    for i, el in enumerate(elements):
        if not el.isSculptObject():
            continue
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if keep_original:
            if collapse_boolean_tree_keep_original(el) is not None:
                count += 1
        else:
            if collapse_boolean_tree(el):
                count += 1

    if preserve_selection and saved and not keep_original:
        # When keep_original=True the duplicate becomes the natural new
        # selection; don't fight that.
        SelectionAPI.restore_selection(saved)

    if count:
        verb: str = "Applied (kept original) on" if keep_original else "Applied bools on"
        show_message(f"{verb} {count} object(s)", 2000)
    else:
        show_error("No sculpt objects in scope", 2000)

    return count


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def apply_selected() -> int:
    """Collapse boolean tree on the current selection."""
    return main(scope=Scope.CURRENT, keep_original=False)


def apply_selected_keep_original() -> int:
    """Duplicate + collapse on selection; original is hidden."""
    return main(scope=Scope.CURRENT, keep_original=True)
