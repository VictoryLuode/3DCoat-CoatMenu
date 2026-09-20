"""
SculptObject_SplitMasked Operator

Split frozen/masked area from a sculpt object into a new object.
Closes holes on both the original and newly created elements.

Uses scope resolution to determine which element to split.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.object_utils import ObjectUtils
from ported.utils.Volume_mode_utils import ensure_surface_mode
from ported.utils.coat_ui_utils import wait_frames, show_message, show_error


# =============================================================================
# MAGIC UI STRINGS
# =============================================================================

CMD_HIDE_FROZEN_AREA: str = "$HideFrozenArea"
CMD_SEPARATE_HIDDEN: str = "$SeparateHidden"
CMD_CLOSE_HOLES: str = "$CloseSurfHoles"
CMD_DIALOG_OK: str = "$DialogButton#1"
SETTING_MAX_CONTOUR_LENGTH: str = "$InputContourLength::MaxContourLength"


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_WAIT_FRAMES: int = 4
DEFAULT_MAX_CONTOUR_LENGTH: int = 999999  # Large value to close all holes


# =============================================================================
# DIALOG CONFIGURATORS
# =============================================================================

def _configure_close_holes_dialog() -> None:
    """Configure and confirm the close holes dialog."""
    coat.ui.setEditBoxValue(SETTING_MAX_CONTOUR_LENGTH,
                            DEFAULT_MAX_CONTOUR_LENGTH)
    coat.ui.cmd(CMD_DIALOG_OK)


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    close_holes: bool = True,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Split masked/frozen area from sculpt object(s).

    Args:
        scope: Which object to operate on (typically CURRENT)
        close_holes: Whether to close holes on both original and new elements
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of new elements created
    """
    from ported.utils.scene_api import SelectionAPI

    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Get elements to process (typically just current)
    elements, _ = resolve_scope_skip_instances(scope)
    if not elements:
        show_error("No object selected", 2000)
        return 0

    total: int = len(elements)
    total_new: int = 0

    for i, element in enumerate(elements):
        if not element.isSculptObject():
            continue

        if progress_callback is not None:
            progress_callback(i, total, element.name())

        new_count: int = _split_element(element, close_holes)
        total_new += new_count

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    if total_new > 0:
        show_message(f"Split created {total_new} new objects", 2000)
    else:
        show_message("No masked area to split", 2000)

    return total_new


def _split_element(element: coat.SceneElement, close_holes: bool) -> int:
    """
    Split a single element's masked/frozen area.

    Args:
        element: The element to split
        close_holes: Whether to close holes on resulting elements

    Returns:
        Number of new elements created
    """
    # Cache parent and existing children BEFORE split
    parent: coat.SceneElement = element.parent()

    # Build a set of existing child element pointers (more reliable than names)
    existing_children: list[coat.SceneElement] = []
    for i in range(parent.childCount()):
        existing_children.append(parent.child(i))

    # Ensure element is selected and in surface mode
    element.selectOne()
    vol: coat.Volume = element.Volume()
    ensure_surface_mode(vol)

    # Hide frozen area, then separate hidden geometry
    coat.ui.cmd(CMD_HIDE_FROZEN_AREA)
    coat.ui.cmd(CMD_SEPARATE_HIDDEN)
    wait_frames(DEFAULT_WAIT_FRAMES)

    # Find newly created elements (elements not in our cached list)
    new_elements: list[coat.SceneElement] = []
    for i in range(parent.childCount()):
        child: coat.SceneElement = parent.child(i)
        is_existing: bool = False
        for existing in existing_children:
            if child == existing:
                is_existing = True
                break
        if not is_existing:
            new_elements.append(child)

    # Close holes ONLY on original element and newly created elements
    if close_holes:
        # Close holes on original element
        element.selectOne()
        wait_frames(1)
        coat.ui.cmd(CMD_CLOSE_HOLES, _configure_close_holes_dialog)
        wait_frames(DEFAULT_WAIT_FRAMES)

        # Close holes on each new element individually
        for new_elem in new_elements:
            new_elem.selectOne()
            wait_frames(1)
            coat.ui.cmd(CMD_CLOSE_HOLES, _configure_close_holes_dialog)
            wait_frames(DEFAULT_WAIT_FRAMES)

    return len(new_elements)
