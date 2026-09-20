"""
Scene Tiling Utilities - Setup tiling grids and instances.

Creates tiled grids of sculpt objects with translational symmetry for seamless tiling.

Pattern:
    from ported.utils.Scene_tiling_utils import TilingParams, setup_tiling_grid
    
    params = TilingParams(base_size=64, use_box=True)
    setup_tiling_grid(params)
"""
import coat
from coat import vec3, Mesh
from dataclasses import dataclass
from enum import Enum

from ported.utils.coat_ui_utils import show_message


# =============================================================================
# SYMMETRY MAGIC UI STRINGS
# =============================================================================

CMD_SYMMETRY: str = "$SYMMETRY"
CMD_SYMMETRY_TRANSLATION: str = "$COMBOBOX_SymmetryTypeTranslation"
CMD_COORD_SYSTEM_XYZ: str = "$COMBOBOX_CoordSystemXYZXYZ_axis"
SETTING_SYMMETRY_ENABLE: str = "$SymmetryParams::EnableSymmetry"
SETTING_SYMMETRY_NUM_X: str = "$SymmetryParams::tNumX"
SETTING_SYMMETRY_NUM_Y: str = "$SymmetryParams::tNumY"
SETTING_SYMMETRY_NUM_Z: str = "$SymmetryParams::tNumZ"
SETTING_SYMMETRY_STEP_X: str = "$SymmetryParams::tStepX"
SETTING_SYMMETRY_STEP_Z: str = "$SymmetryParams::tStepZ"


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_BASE_SIZE: int = 64
DEFAULT_THICKNESS: int = 16
DEFAULT_BORDER_RATIO: float = 0.25  # Border = base_size * ratio


# =============================================================================
# PRIMITIVE TYPE ENUM
# =============================================================================

class PrimitiveType(Enum):
    """Type of primitive to create for tiling."""
    PLANE = "plane"
    BOX = "box"


# =============================================================================
# TILING PARAMS DATACLASS
# =============================================================================

@dataclass
class TilingParams:
    """Parameters for tiling grid setup."""
    base_size: int = DEFAULT_BASE_SIZE
    thickness: int = DEFAULT_THICKNESS
    border_ratio: float = DEFAULT_BORDER_RATIO
    primitive_type: PrimitiveType = PrimitiveType.PLANE


# =============================================================================
# INSTANCE FUNCTIONS
# =============================================================================

def duplicate_as_instance(
    source: coat.SceneElement,
    location: vec3
) -> coat.SceneElement:
    """
    Duplicate a scene element as an instance at a given location.

    Args:
        source: The source element to duplicate
        location: The location to place the instance

    Returns:
        The created instance element
    """
    inst: coat.SceneElement = source.duplicateAsInstance()
    transform: coat.mat4 = inst.getTransform()
    transform.SetTranslation(location)
    inst.setTransform(transform)
    inst.rename(f"Instance {location.x}, {location.y}, {location.z}")
    return inst


def create_grid_instance_locations(base_size: int) -> list[vec3]:
    """
    Create a 3x3 grid of instance locations around the origin.

    Returns 8 locations (excludes center which is the original).

    Args:
        base_size: The spacing between instances

    Returns:
        List of vec3 locations for instances
    """
    return [
        # Top row
        vec3(-base_size, 0, base_size),
        vec3(0, 0, base_size),
        vec3(base_size, 0, base_size),
        # Middle row (left and right, center is original)
        vec3(-base_size, 0, 0),
        vec3(base_size, 0, 0),
        # Bottom row
        vec3(-base_size, 0, -base_size),
        vec3(0, 0, -base_size),
        vec3(base_size, 0, -base_size),
    ]


# =============================================================================
# SYMMETRY SETUP
# =============================================================================

def disable_symmetry() -> None:
    """Disable symmetry mode."""
    coat.ui.cmd(CMD_SYMMETRY)
    coat.ui.setBoolValue(SETTING_SYMMETRY_ENABLE, False)


def setup_translation_symmetry(step_x: float, step_z: float) -> None:
    """
    Configure translational symmetry for seamless tiling.

    Args:
        step_x: Step size in X direction
        step_z: Step size in Z direction
    """
    coat.ui.cmd(CMD_SYMMETRY)
    coat.ui.setBoolValue(SETTING_SYMMETRY_ENABLE, True)
    coat.ui.cmd(CMD_SYMMETRY_TRANSLATION)
    coat.ui.setSliderValue(SETTING_SYMMETRY_NUM_X, 1)
    coat.ui.setSliderValue(SETTING_SYMMETRY_NUM_Y, 0)
    coat.ui.setSliderValue(SETTING_SYMMETRY_NUM_Z, 1)
    coat.ui.setSliderValue(SETTING_SYMMETRY_STEP_X, step_x)
    coat.ui.setSliderValue(SETTING_SYMMETRY_STEP_Z, step_z)
    coat.ui.cmd(CMD_COORD_SYSTEM_XYZ)


# =============================================================================
# PRIMITIVE CREATION
# =============================================================================

def create_plane_mesh(size: int, divisions: int) -> Mesh:
    """Create a plane mesh for tiling."""
    return Mesh.plane(
        center=vec3(0, 0, 0),
        sizeX=size,
        sizeY=size,
        divisionsX=divisions,
        divisionsY=divisions,
        xAxis=vec3.AxisX,
        yAxis=vec3.AxisZ
    )


def create_box_mesh(size: int, thickness: int) -> Mesh:
    """Create a box mesh for tiling."""
    return Mesh.box(
        size=vec3(size, thickness, size),
        yAxis=vec3(0, 1, 0),
        center=vec3(0, -float(thickness) / 2.0, 0),
        detail_size=1,
        fillet=0
    )


# =============================================================================
# MAIN TILING SETUP FUNCTION
# =============================================================================

def tile_existing_object(
    source: coat.SceneElement,
    tile_size: int = DEFAULT_BASE_SIZE,
    enable_symmetry: bool = True,
) -> list[coat.SceneElement]:
    """
    Create a 3x3 tiling grid around an existing sculpt object.

    Creates 8 instances around the source object and optionally enables
    translational symmetry for seamless editing.

    Args:
        source: The source sculpt element to tile
        tile_size: Spacing between instances (default 64)
        enable_symmetry: Whether to enable translational symmetry

    Returns:
        List of created instance elements (excludes source)
    """
    # Disable symmetry during setup
    disable_symmetry()

    # Create instance locations
    locations: list[vec3] = create_grid_instance_locations(tile_size)
    instances: list[coat.SceneElement] = []

    # Create instances
    for loc in locations:
        inst: coat.SceneElement = duplicate_as_instance(source, loc)
        instances.append(inst)

    # Parent all instances under source
    for inst in instances:
        inst.changeParent(source)

    # Select source element
    source.selectOne()

    # Optionally setup translational symmetry
    if enable_symmetry:
        setup_translation_symmetry(float(tile_size), float(tile_size))

    show_message(
        f"Instance tiling complete ({len(instances)} instances created)",
        4000
    )

    return instances


def setup_tiling_grid(params: TilingParams) -> coat.SceneElement:
    """
    Setup a complete tiling grid with a new primitive and symmetry.

    Args:
        params: TilingParams with configuration

    Returns:
        The center sculpt element
    """
    # Calculate sizes
    border: int = int(params.base_size * params.border_ratio)
    size: int = params.base_size + border

    # Disable symmetry during setup
    disable_symmetry()

    # Get scene root
    root: coat.SceneElement = coat.Scene.sculptRoot()

    # Create center element
    center_element: coat.SceneElement = root.addChild(
        f"Center Plane ({params.base_size}x{params.base_size})"
    )
    center_volume: coat.Volume = center_element.Volume()
    center_volume.toSurface()

    # Create appropriate mesh
    if params.primitive_type == PrimitiveType.BOX:
        mesh: Mesh = create_box_mesh(size, params.thickness)
    else:
        mesh: Mesh = create_plane_mesh(size, size)

    center_volume.mergeMesh(mesh)

    # Create instances
    locations: list[vec3] = create_grid_instance_locations(params.base_size)
    instances: list[coat.SceneElement] = []

    for loc in locations:
        inst: coat.SceneElement = duplicate_as_instance(center_element, loc)
        instances.append(inst)

    # Parent all instances under center
    for inst in instances:
        inst.changeParent(center_element)

    # Select center element
    center_element.selectOne()

    # Setup translational symmetry
    setup_translation_symmetry(
        float(params.base_size), float(params.base_size))

    show_message(
        f"Tiling grid setup complete ({len(instances) + 1} tiles)",
        4000
    )

    return center_element
