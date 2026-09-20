"""
SculptObject_NewVoxBool Operator

Create a NEW voxel boolean child object under the selected sculpt object.
This clones the parent, parents the clone under it and assigns a live boolean mode.

Supports subtract, intersect, and union boolean operations.
Handles voxelization of parent and proper ordering of operations
to prevent crashes (extrusion before boolean mode for intersect).

Uses scope resolution to determine parent element.
"""
import coat
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
DEFAULT_EXTRUSION: float = 1.0


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    mode: BooleanMode = BooleanMode.SUBTRACT,
    extrusion_amount: float = DEFAULT_EXTRUSION,
    min_voxel_polycount: int = DEFAULT_MIN_POLYCOUNT,
) -> coat.SceneElement | None:
    """
    Create a NEW voxel boolean child for the current element.

    Clones the selected object, parents the clone under it and assigns
    the requested live boolean mode. Parent is voxelised first if needed.

    Args:
        mode: The boolean mode (SUBTRACT, INTERSECT, UNION)
        extrusion_amount: Extrusion amount for INTERSECT mode
        min_voxel_polycount: Minimum polycount when voxelising parent

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
        # Select only the new child so the user can sculpt it immediately
        child.selectOne()
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


def intersect(extrusion: float = DEFAULT_EXTRUSION) -> coat.SceneElement | None:
    """Create an intersect boolean child with extrusion."""
    return main(mode=BooleanMode.INTERSECT, extrusion_amount=extrusion)


def union() -> coat.SceneElement | None:
    """Create a union boolean child."""
    return main(mode=BooleanMode.UNION)
