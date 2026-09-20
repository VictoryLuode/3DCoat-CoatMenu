"""
Reduce polycount by half using resample + voxel conversion.

This reduces the polycount of the current object by half using resample,
then converts to voxels to lock in the new density.

Room: Sculpt
Action: Resample to half, then convert to voxels
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Reduce polycount by half using resample + voxel conversion."""
    import coat
    from ported.utils.object_utils import ObjectUtils
    from ported.utils.Volume_resample_utils import resample_to_half
    from ported.utils.Volume_mode_utils import ensure_surface_mode
    from ported.utils.coat_ui_utils import show_message

    # Get current sculpt object and volume with validation
    result = ObjectUtils.get_current_sculpt_volume()
    if not result:
        return

    current_object, vol = result

    # Validate object has polygons
    if not ObjectUtils.validate_volume_has_polygons(vol):
        return

    # If it's voxelized, convert to surface first
    ensure_surface_mode(vol)

    # Get current polycount
    current_polycount: int = vol.getPolycount()
    target_polycount: int = current_polycount // 2

    print(f"Reducing: {current_polycount:,} -> {target_polycount:,}")

    # Resample to half
    resample_to_half(current_polycount)

    # Convert to voxels
    vol.toVoxels()

    new_polycount: int = vol.getPolycount()
    show_message(f"Reduced to {new_polycount:,} polys", 3000)




main()
