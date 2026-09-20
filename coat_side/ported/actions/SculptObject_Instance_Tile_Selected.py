"""
Create a 3x3 tiling grid around the selected sculpt object.

Creates 8 instances around the selected object and enables translational
symmetry for seamless tiling. Useful for sculpting textures or patterns
that need to tile seamlessly.

Room: Sculpt
Action: Creates 8 instances around selected object with tiling symmetry
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Create instance tiles around the selected object."""
    from ported.utils.scene_api import SceneAPI
    from ported.utils.Scene_tiling_utils import tile_existing_object
    from ported.utils.coat_ui_utils import show_error

    source: "coat.SceneElement | None" = SceneAPI.get_current_element()
    if not source:
        show_error("No object selected", 2000)
        return

    if not source.isSculptObject():
        show_error("Selected element is not a sculpt object", 2000)
        return

    # Create tiling grid with default size (64 units)
    tile_existing_object(source, tile_size=64, enable_symmetry=True)


main()
