"""
Volume Mode Utilities - Surface/Voxel conversion on Volumes.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Operators in `_ops/` own Config dataclasses and call these functions.

Uses native `volume.toSurface()` / `volume.toVoxels()` API methods from coat.pyi.
There are NO `$ToVoxels` / `$ToSurface` UI commands - those were hallucinated.
"""
import coat

from ported.utils.coat_ui_utils import wait_frames
from ported.utils.Volume_resample_utils import resample_to_target

# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_VOXELIZE_POLYCOUNT: int = 100000
MESH_OP_WAIT_FRAMES: int = 4


# =============================================================================
# EXECUTE FUNCTIONS (raw args)
# =============================================================================

def execute_voxelize(
    suggested_polycount: int = DEFAULT_VOXELIZE_POLYCOUNT,
    volume: coat.Volume | None = None,
) -> None:
    """
    Voxelize a Volume.

    `suggested_polycount` is accepted for API compatibility but is not honored
    by the native `toVoxels()` method (which has no polycount argument).

    Args:
        suggested_polycount: Ignored (kept for backwards compatibility)
        volume: Volume to voxelize. If None, uses the current active volume
            (obtained via ``coat.Scene.current().Volume()``).
    """
    if volume is None:
        scene: coat.Scene = coat.Scene.current()
        volume = scene.Volume()
    if volume.isSurface():
        polycount: int = volume.getPolycount()
        if polycount <= 0:
            print("[execute_voxelize] skip: zero polycount")
            return
        resample_to_target(polycount, polycount)  # nudged to 1.02x by _avoid_noop()
        volume.toVoxels()
        wait_frames(MESH_OP_WAIT_FRAMES)


# =============================================================================
# CONVERSION FUNCTIONS (operate on Volume directly)
# =============================================================================

def convert_to_surface(volume: coat.Volume) -> None:
    """Convert a volume from voxels to surface mode."""
    if volume.isVoxelized():
        volume.toSurface()
        wait_frames(MESH_OP_WAIT_FRAMES)


def convert_to_voxels(volume: coat.Volume, polycount: int | None = None) -> None:
    """
    Convert a volume from surface to voxels using the native API.

    Args:
        volume: The volume to convert
        polycount: Ignored (native toVoxels() has no polycount argument)
    """
    if volume.isSurface():
        pc: int = volume.getPolycount()
        if pc <= 0:
            print("[convert_to_voxels] skip: zero polycount")
            return
        resample_to_target(pc, pc)  # nudged to 1.02x by _avoid_noop()
        volume.toVoxels()
        wait_frames(MESH_OP_WAIT_FRAMES)


def ensure_surface_mode(volume: coat.Volume) -> None:
    """Ensure volume is in surface mode (convert from voxels if needed)."""
    convert_to_surface(volume)


def convert_to_voxels_safe(volume: coat.Volume) -> None:
    """
    Voxelize a surface volume using the native API.

    Pre-resamples to current polycount (nudged to 1.02x) before voxelizing
    to ensure a clean mesh rebuild, avoiding corruption on certain topologies.

    Args:
        volume: A surface-mode volume to convert
    """
    if volume.isSurface():
        pc: int = volume.getPolycount()
        if pc <= 0:
            print("[convert_to_voxels_safe] skip: zero polycount")
            return
        resample_to_target(pc, pc)  # nudged to 1.02x by _avoid_noop()
        volume.toVoxels()
        wait_frames(MESH_OP_WAIT_FRAMES)


def ensure_voxel_mode(volume: coat.Volume) -> None:
    """Ensure volume is in voxel mode (convert from surface if needed)."""
    if volume.isSurface():
        convert_to_voxels_safe(volume)


def voxelize_to_polycount(target_polycount: int) -> None:
    """
    Voxelize current Volume.

    `target_polycount` is accepted for API compatibility but ignored
    (native toVoxels() has no polycount argument).
    """
    execute_voxelize(target_polycount)


# =============================================================================
# RESAMPLE + VOXELIZE WORKFLOW
# =============================================================================

def resample_and_voxelize(volume: coat.Volume, multiplier: float) -> int:
    """
    Voxelize a surface volume at Nx polycount.

    If already voxelized, converts back to surface.

    Note: native `toVoxels()` does not accept a target polycount; the multiplier
    is applied via a pre-resample pass on the surface mesh before voxelization.

    Args:
        volume: The volume to process
        multiplier: Polycount multiplier (2.0 = 2x, 4.0 = 4x, etc.)

    Returns:
        New polycount after operation
    """
    if volume.isVoxelized():
        # Already voxel - convert to surface
        volume.toSurface()
        wait_frames(MESH_OP_WAIT_FRAMES)
        return volume.getPolycount()

    # Surface mode - resample to multiplied polycount, then voxelize
    current_polycount: int = volume.getPolycount()
    if current_polycount <= 0:
        return 0

    target_polycount: int = int(current_polycount * multiplier)
    # Local import to avoid circular dependency
    from ported.utils.Volume_resample_utils import resample_to_target
    resample_to_target(current_polycount, target_polycount)
    wait_frames(2)
    volume.toVoxels()
    wait_frames(MESH_OP_WAIT_FRAMES)

    return volume.getPolycount()
