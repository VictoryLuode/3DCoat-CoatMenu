"""
SculptObject_VoxBool Operator

Create live boolean children for sculpt objects.

Supports subtract, intersect, and union boolean operations.
Handles voxelization of parent and proper ordering of operations
to prevent crashes (extrusion before boolean mode for intersect).

Uses scope resolution to determine parent element.
"""
import coat
from enum import Enum
from ported.utils.scene_api import SceneAPI
from ported.utils.SceneElement_boolean_utils import (
    create_boolean_child, BooleanMode
)
from ported.utils.Volume_mode_utils import convert_to_voxels
from ported.utils.coat_ui_utils import wait_frames, show_message, show_error


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_MIN_POLYCOUNT: int = 50000
DEFAULT_WAIT_FRAMES: int = 4


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    mode: BooleanMode = BooleanMode.SUBTRACT,
    extrusion_amount: float = 0.2,
    min_voxel_polycount: int = DEFAULT_MIN_POLYCOUNT,
) -> coat.SceneElement | None:
    """
    Create a live boolean child for the current element.

    Args:
        mode: The boolean mode (SUBTRACT, INTERSECT, UNION)
        extrusion_amount: Extrusion amount for INTERSECT mode
        min_voxel_polycount: Minimum polycount when voxelizing parent

    Returns:
        The created child element, or None if failed
    """
    parent: coat.SceneElement | None = SceneAPI.get_current_element()
    if not parent:
        show_error("No object selected", 2000)
        return None

    if not parent.isSculptObject():
        show_error("Selected element is not a sculpt object", 2000)
        return None

    # Ensure parent is voxel mode (required for live booleans)
    vol: coat.Volume = parent.Volume()
    if not vol.isVoxelized():
        polycount: int = vol.getPolycount()
        target: int = max(polycount, min_voxel_polycount)
        convert_to_voxels(vol, target)
        wait_frames(DEFAULT_WAIT_FRAMES)

    # Create boolean child based on mode
    # SUBTRACT/UNION: clear child content (user sculpts new geometry)
    # INTERSECT: apply extrusion (keep geometry, extrude BEFORE boolean mode)
    if mode == BooleanMode.INTERSECT:
        child: coat.SceneElement | None = create_boolean_child(
            parent, mode,
            apply_extrusion=True,
            extrusion_amount=extrusion_amount,
            clear_child=False
        )
    else:
        child = create_boolean_child(
            parent, mode,
            apply_extrusion=False,
            clear_child=True
        )

    if child:
        mode_name: str = mode.name.lower()
        show_message(f"Created {mode_name}: {child.name()}", 2000)
    else:
        show_error(f"Failed to create {mode.name.lower()} child", 2000)

    return child


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def subtract() -> coat.SceneElement | None:
    """Create a subtract boolean child."""
    return main(mode=BooleanMode.SUBTRACT)


def intersect(extrusion: float = 0.2) -> coat.SceneElement | None:
    """Create an intersect boolean child with extrusion."""
    return main(mode=BooleanMode.INTERSECT, extrusion_amount=extrusion)


def union() -> coat.SceneElement | None:
    """Create a union boolean child."""
    return main(mode=BooleanMode.UNION)
