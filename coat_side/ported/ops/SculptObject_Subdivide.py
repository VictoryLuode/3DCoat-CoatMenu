"""
SculptObject_Subdivide Operator

Subdivide sculpt objects to increase polygon count.
Each subdivision approximately doubles the polycount.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.Volume_subdivide_utils import subdivide_once
from ported.utils.Volume_mode_utils import ensure_surface_mode
from ported.utils.Scene_cleanup_utils import cleanup_after_mesh_operation
from ported.utils.coat_ui_utils import show_message, show_error


# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_SUBDIVISIONS: int = 1
MAX_SUBDIVISIONS: int = 4


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _subdivide_element(
    element: coat.SceneElement,
    subdivisions: int = DEFAULT_SUBDIVISIONS,
) -> bool:
    """
    Subdivide a single element.

    Returns:
        True if element was subdivided, False if skipped
    """
    if not element.isSculptObject():
        return False

    vol: coat.Volume = element.Volume()
    ensure_surface_mode(vol)

    # Select element for operation
    element.selectOne()

    for _ in range(subdivisions):
        subdivide_once()

    return True


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    subdivisions: int = DEFAULT_SUBDIVISIONS,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Subdivide objects to increase polygon count.

    Args:
        scope: Which objects to subdivide
        subdivisions: Number of subdivisions (1-4, each roughly doubles polys)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects subdivided
    """
    # Clamp subdivisions
    subdivisions = max(1, min(subdivisions, MAX_SUBDIVISIONS))

    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validation for scope check should use a separate variable
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Resolve which elements to operate on
    elements, _ = resolve_scope_skip_instances(scope)

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    total: int = len(elements)

    # Subdivide each element
    count: int = 0
    for i, el in enumerate(elements):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if _subdivide_element(el, subdivisions):
            count += 1

    # Cleanup after mesh operations
    cleanup_after_mesh_operation()

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    # Build status message
    multiplier: int = 2 ** subdivisions
    status: str = f"Subdivided {count} objects ({multiplier}x polys)"

    show_message(status, 2000)
    return count
