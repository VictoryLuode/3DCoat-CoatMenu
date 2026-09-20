"""
SculptObject_RemeshPreserveParts Operator

Remesh a surface object while preserving its parts.

Process:
1. Decompose the object into separate parts
2. Convert each part to voxels and back to surface (remesh)
3. Merge all parts back together
4. Reset to global space

This preserves the topology of separate parts while cleaning up mesh quality.

Uses scope resolution to determine which element to process.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope
from ported.utils.Volume_mode_utils import ensure_surface_mode
from ported.utils.coat_ui_utils import (
    wait_frames, show_message, show_error,
    CMD_DECOMPOSE, CMD_DIALOG_OK, CMD_TO_GLOBAL_SPACE
)


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_WAIT_FRAMES: int = 4


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _decompose_object(element: coat.SceneElement) -> None:
    """Decompose an object into its constituent parts."""
    element.selectOne()

    def decompose_confirm() -> None:
        coat.ui.cmd(CMD_DIALOG_OK)

    coat.ui.cmd(CMD_DECOMPOSE, decompose_confirm)
    wait_frames(DEFAULT_WAIT_FRAMES)


def _remesh_element(element: coat.SceneElement) -> bool:
    """
    Remesh a single element by converting to voxels and back.

    Args:
        element: The element to remesh

    Returns:
        True if successful
    """
    if not element.isSculptObject():
        return False

    element.selectOne()
    vol: coat.Volume = element.Volume()

    # Skip if empty or invalid
    if vol.getPolycount() <= 0:
        return False

    # Ensure surface mode first
    ensure_surface_mode(vol)

    # Voxelize and back to surface to remesh
    vol.toVoxels()
    vol.toSurface()

    return True


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Remesh object while preserving parts via decompose and merge.

    Args:
        scope: Which object to process (typically CURRENT for single object)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of parts processed
    """
    # Get the root element
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if not current:
        show_error("No object selected", 2000)
        return 0

    if not current.isSculptObject():
        show_error("Selected element is not a sculpt object", 2000)
        return 0

    # Save selection
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    print(f"Starting remesh with preserve parts: {current.name()}")

    # Decompose object into parts
    _decompose_object(current)

    # Remesh each part in subtree
    subtree: list[coat.SceneElement] = SceneAPI.collect_subtree(current)
    total: int = len(subtree)
    count: int = 0
    for i, el in enumerate(subtree):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if _remesh_element(el):
            count += 1

    # Select root and ensure surface mode
    current.selectOne()
    vol: coat.Volume = current.Volume()
    ensure_surface_mode(vol)

    # Merge subtree back together
    current.mergeSubtree()

    # Reset to global space
    coat.ui.cmd(CMD_TO_GLOBAL_SPACE)

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    show_message(f"Remeshed with parts preserved: {count} parts", 2000)
    return count
