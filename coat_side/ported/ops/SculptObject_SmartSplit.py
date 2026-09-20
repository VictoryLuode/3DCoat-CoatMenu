"""
SculptObject_SmartSplit Operator

Smart split operator that adapts based on object mode:
- Voxel mode: Separates hidden geometry directly
- Surface mode: Hides masked/frozen area, then separates hidden geometry

Closes holes on both original and newly created elements in both modes.
Uses scope resolution to determine which element(s) to split.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.Volume_resample_utils import execute_resample_scale_only
from ported.utils.coat_ui_utils import wait_frames, show_message, show_error


# =============================================================================
# MAGIC UI STRINGS
# =============================================================================

CMD_HIDE_FROZEN_AREA: str = "$HideFrozenArea"
CMD_SEPARATE_HIDDEN: str = "$SeparateHidden"
CMD_DELETE_HIDDEN: str = "$DeleteHidden"
CMD_INVERT_HIDE: str = "$InvertHide"
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
    Smart split: adapts based on voxel vs surface mode.

    Voxel mode: Separates hidden geometry directly
    Surface mode: Hides masked/frozen area first, then separates

    Args:
        scope: Which object(s) to operate on
        close_holes: Whether to close holes on both original and new elements
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of new elements created
    """
    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Get elements to process
    elements, _ = resolve_scope_skip_instances(scope)
    if not elements:
        show_error("No object selected", 2000)
        return 0

    total: int = len(elements)
    total_new: int = 0
    voxel_count: int = 0
    surface_count: int = 0

    for i, element in enumerate(elements):
        if not element.isSculptObject():
            continue

        if progress_callback is not None:
            progress_callback(i, total, element.name())

        vol: coat.Volume = element.Volume()

        # Determine mode and call appropriate split method
        if vol.isVoxelized():
            new_count: int = _split_voxel_element(element, close_holes)
            voxel_count += 1

        elif vol.isSurface():
            new_count: int = _split_surface_element(element, close_holes)
            surface_count += 1

        else:
            # Unknown mode, skip
            continue

        total_new += new_count

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    # Generate informative message based on what was processed
    if total_new > 0:
        mode_info: str = ""
        if voxel_count > 0 and surface_count > 0:
            mode_info = " (mixed: voxel split hidden, surface split masked/hidden + closed holes)"
        elif voxel_count > 0:
            mode_info = " (voxel mode: split hidden volumes)"
        elif surface_count > 0:
            mode_info = " (surface mode: split masked/hidden + closed holes)"

        show_message(
            f"Smart split created {total_new} new object(s){mode_info}", 3000)
    else:
        show_message("No hidden/masked area to split", 2000)

    return total_new


# =============================================================================
# MODE-SPECIFIC SPLIT FUNCTIONS
# =============================================================================

def _split_voxel_element(element: coat.SceneElement, close_holes: bool) -> int:
    """
    Split voxel mode element using duplicate + invert-hide approach.

    This avoids $SeparateHidden which loses colored-surface data.

    Voxel path:
    1. $InvertHide             - flip hidden↔visible (visible→hidden, hidden→visible)
    2. duplicate()              - clone with only shown voxels, no hide state
    3. Original: $InvertHide    - restore original hide state on original
    4. Original: $DeleteHidden  - original keeps only what was originally VISIBLE

    The duplicate is produced with only the currently-shown voxels
    (originally-hidden) and no hide state — it needs no further processing.

    Note: close_holes is intentionally skipped — $CloseSurfHoles is a
    surface command and is not meaningful in voxel mode.

    Args:
        element: The voxel element to split
        close_holes: Ignored for voxel path

    Returns:
        Number of new elements created (always 1 if successful, 0 on failure)
    """
    coat.ui.cmd(CMD_INVERT_HIDE)
    wait_frames(5)
    dupe: coat.SceneElement | None = element.duplicate()
    wait_frames(5)
    dupe.removeSubtree()
    wait_frames(5)
    dupe.selectOne()
    wait_frames(5)

    # Dupe inherits only the shown (originally-hidden) voxels with no
    # hide state — it is already the correct split result.
    dupe_vol: coat.Volume = dupe.Volume()

    # Early-out: if dupe has zero polygons, nothing was hidden — clean up
    # and restore the original hide state before returning.
    if dupe_vol and dupe_vol.getPolycount() <= 0:
        dupe.selectOne()
        dupe.remove()
        coat.ui.cmd(CMD_INVERT_HIDE)
        show_message(
            "No polygons were produced: use voxhide to hide voxels", 3000)
        return 0

    # Original: restore hide state, then delete the still-hidden
    # (originally-hidden) voxels, keeping only the originally-visible side.
    element.selectOne()
    coat.ui.cmd(CMD_INVERT_HIDE)
    coat.ui.cmd(CMD_DELETE_HIDDEN)

    # Force resample on duplicate to stabilize voxel data after split.
    dupe.selectOne()
    # wait_frames(1)
    dupe_vol = dupe.Volume()
    if dupe_vol and dupe_vol.isVoxelized():
        polycount: int = dupe_vol.getPolycount()
        if polycount > 0:
            execute_resample_scale_only(ratio=1.1)

    dupe.selectOne()
    return 1


def _split_surface_element(element: coat.SceneElement, close_holes: bool) -> int:
    """
    Split surface mode element (hides masked/frozen, then separates hidden).

    Early-out: if the split produces zero-polygon elements, they are deleted
    and a warning is shown ("use masked area to split"). Only elements with
    actual geometry survive to the close-holes step.

    Args:
        element: The surface element to split
        close_holes: Whether to close holes on resulting elements

    Returns:
        Number of new elements created (0 if nothing was masked/frozen)
    """
    # Cache parent and existing children BEFORE split
    parent: coat.SceneElement = element.parent()

    existing_children: list[coat.SceneElement] = []
    for i in range(parent.childCount()):
        existing_children.append(parent.child(i))

    # Ensure element is selected (already in surface mode)
    element.selectOne()

    # In surface mode: hide frozen/masked area first, then separate
    coat.ui.cmd(CMD_HIDE_FROZEN_AREA)
    coat.ui.cmd(CMD_SEPARATE_HIDDEN)
    # wait_frames(DEFAULT_WAIT_FRAMES)

    # Find newly created elements, filtering out zero-poly empties.
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

    # Early-out: delete zero-polygon new elements. If none survive,
    # restore selection on the original and warn.
    survivors: list[coat.SceneElement] = []
    for new_elem in new_elements:
        new_vol: coat.Volume = new_elem.Volume()
        if new_vol and new_vol.getPolycount() > 0:
            survivors.append(new_elem)
        else:
            new_elem.removeSubtree()
            # wait_frames(1)

    if not survivors:
        element.selectOne()
        show_message(
            "No polygons were produced: use masked area to split", 3000)
        return 0

    # Close holes on original element and surviving new elements if requested
    if close_holes:
        # Close holes on original element
        element.selectOne()
        # wait_frames(1)
        coat.ui.cmd(CMD_CLOSE_HOLES, _configure_close_holes_dialog)
        # wait_frames(DEFAULT_WAIT_FRAMES)

        # Close holes on each surviving new element
        for new_elem in survivors:
            new_elem.selectOne()
            # wait_frames(1)
            coat.ui.cmd(CMD_CLOSE_HOLES, _configure_close_holes_dialog)
            # wait_frames(DEFAULT_WAIT_FRAMES)

    # Make the new split object the active selection.
    survivors[0].selectOne()
    return len(survivors)
