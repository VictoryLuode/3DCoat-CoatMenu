"""
SculptObject_ModeConvert Operator

Convert sculpt objects between surface and voxel modes.
Supports: to surface, to voxels with optional polycount.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from enum import Enum
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.Volume_mode_utils import (
    convert_to_surface,
    convert_to_voxels,
    resample_and_voxelize,
)
from ported.utils.Scene_cleanup_utils import cleanup_after_mesh_operation
from ported.utils.coat_ui_utils import show_message, show_error


class ConvertMode(Enum):
    """Conversion mode."""
    TO_SURFACE = "surface"
    TO_VOXELS = "voxels"
    RESAMPLE_VOXELIZE = "resample_voxelize"  # Resample Nx then voxelize


# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_VOXELIZE_POLYCOUNT: int = 100000
DEFAULT_RESAMPLE_MULTIPLIER: float = 2.0


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _convert_element(
    element: coat.SceneElement,
    mode: ConvertMode,
    polycount: int | None = None,
    multiplier: float = DEFAULT_RESAMPLE_MULTIPLIER,
) -> bool:
    """
    Convert a single element.

    Returns:
        True if element was converted, False if skipped
    """
    if not element.isSculptObject():
        return False

    vol: coat.Volume = element.Volume()

    # Skip empty voxel layers and other zero-polycount elements
    if vol.getPolycount() <= 0:
        print(
            f"[ModeConvert] SKIP '{element.name()}': "
            f"zero polycount (empty voxel layer)"
        )
        return False

    element.selectOne()
    coat.io.step(1)  # Wait for 3DCoat to register new active selection

    if mode == ConvertMode.TO_SURFACE:
        convert_to_surface(vol)
    elif mode == ConvertMode.TO_VOXELS:
        convert_to_voxels(vol, polycount)
    elif mode == ConvertMode.RESAMPLE_VOXELIZE:
        resample_and_voxelize(vol, multiplier)

    return True


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    mode: ConvertMode = ConvertMode.TO_SURFACE,
    polycount: int | None = None,
    multiplier: float = DEFAULT_RESAMPLE_MULTIPLIER,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Convert objects between surface and voxel modes.

    Args:
        scope: Which objects to convert
        mode: Conversion mode (TO_SURFACE, TO_VOXELS, RESAMPLE_VOXELIZE)
        polycount: Target polycount for voxelization (if set)
        multiplier: Polycount multiplier for RESAMPLE_VOXELIZE mode
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects converted
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

    # Resolve which elements to operate on
    elements, _ = resolve_scope_skip_instances(scope)

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    total: int = len(elements)

    # Convert each element
    count: int = 0
    for i, el in enumerate(elements):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if _convert_element(el, mode, polycount, multiplier):
            count += 1

    # Cleanup after mesh operations
    cleanup_after_mesh_operation()

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    # Build status message
    if mode == ConvertMode.TO_SURFACE:
        status: str = f"Converted {count}/{total} to surface"
    elif mode == ConvertMode.TO_VOXELS:
        status = f"Converted {count}/{total} to voxels"
    else:
        status = f"Resampled+voxelized {count}/{total} ({multiplier:.0f}x)"

    show_message(f"{status}", 2000)
    return count
