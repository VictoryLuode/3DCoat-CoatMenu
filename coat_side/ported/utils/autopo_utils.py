"""
Autopo Utilities - Workflow automation for autopo operations.

Provides dataclasses and functions to run autopo with typed parameters
and import results back to sculpt room in various configurations.

Pattern:
    params = AutopoParams(target_polycount=10000, bypass_density_modal=True)
    execute_autopo(params)
"""
import coat
from dataclasses import dataclass
from typing import Callable
from enum import Enum

from ported.utils.coat_ui_utils import (
    switch_to_room,
    ensure_sculpt_room,
    show_message,
    show_error,
    wait_frames,
    ROOM_SCULPT,
    ROOM_RETOPO,
    CMD_DIALOG_OK,
)

# =============================================================================
# AUTOPO MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

# Command to open autopo dialog (Quadrangulate opens the dialog)
CMD_AUTOPO: str = "$Quadrangulate"

# Import commands
CMD_RETOPO_TO_SCULPT: str = "$GetObjectFromRetopoRoom"
CMD_IMPORT_MULTIRES: str = "$MultiresControl::AddLowMultiresolutionLevelFromRetopo[1]"
CMD_CLEAR_RETOPO: str = "$ClearTM"

# Dialog OK button
CMD_DIALOG_OK_LOCAL: str = "$DialogButton#1"

# Quality combobox and options
COMBOBOX_QUAD_QUALITY: str = "COMBOBOX_QuadQuality"
QUALITY_DRAFT: str = "$COMBOBOX_QuadQualityqDraft"
QUALITY_INTERMEDIATE: str = "$COMBOBOX_QuadQualityqIntermediate"
QUALITY_BEST: str = "$COMBOBOX_QuadQualityqBestQuality"

# Autopo parameter settings (QuadragulationTask namespace)
SETTING_REQUIRED_POLYCOUNT: str = "$QuadragulationTask::RequiredPolycount"
SETTING_CAPTURE_DETAILS: str = "$QuadragulationTask::CaptureDetails"
SETTING_HARDSURFACE: str = "$QuadragulationTask::HardsurfaceRetopology"
SETTING_AUTO_DENSITY: str = "$QuadragulationTask::AutoDensityInfluence"
SETTING_VOXELIZE: str = "$QuadragulationTask::Voxelize"
SETTING_VOXELIZE_POLYCOUNT: str = "$QuadragulationTask::VoxelizedObjectPolycount1"
SETTING_DECIMATE_IF_ABOVE: str = "$QuadragulationTask::DecimateIfAbove"
SETTING_DECIMATION_LIMIT: str = "$QuadragulationTask::DecimationLimit1"
SETTING_TANGENT_SMOOTH: str = "$QuadragulationTask::TangentSmoothRes"
SETTING_BYPASS_DENSITY_MODAL: str = "$QuadragulationTask::BypassDensityAndStrokes"

# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_TARGET_POLYCOUNT: int = 10000
DEFAULT_CAPTURE_DETAILS: float = 1.0  # 0.0-1.0 (1.0 = 100%)
DEFAULT_AUTO_DENSITY: float = 0.5  # 0.0-2.0 (painted density influence)
DEFAULT_HARDSURFACE: bool = False
DEFAULT_VOXELIZE: bool = False
# x1000 polys (1000 = 1M) - voxelize target polycount
DEFAULT_VOXELIZE_POLYCOUNT: int = 1000
DEFAULT_DECIMATE_IF_ABOVE: bool = False
# x1000 polys (10 = 10k) - decimate if exceeds
DEFAULT_DECIMATION_LIMIT: int = 10
DEFAULT_TANGENT_SMOOTH: bool = True
DEFAULT_BYPASS_DENSITY_MODAL: bool = True
DEFAULT_QUALITY: str = "intermediate"  # draft, intermediate, best

# Timing defaults
AUTOPO_WAIT_FRAMES: int = 8
IMPORT_WAIT_FRAMES: int = 4


# =============================================================================
# QUALITY ENUM
# =============================================================================

class QuadQuality(Enum):
    """Quadrangulation quality preset."""
    DRAFT = "draft"
    INTERMEDIATE = "intermediate"
    BEST = "best"


# =============================================================================
# AUTOPO DATACLASS & CONFIGURATOR
# =============================================================================

@dataclass
class AutopoParams:
    """
    Parameters for autopo (automatic retopology) operation.

    Users don't need to know magic strings - just set these typed fields.
    """
    target_polycount: int = DEFAULT_TARGET_POLYCOUNT
    capture_details: float = DEFAULT_CAPTURE_DETAILS  # 0.0-1.0 (1.0 = 100%)
    auto_density: float = DEFAULT_AUTO_DENSITY  # 0.0-2.0 (painted density)
    hardsurface: bool = DEFAULT_HARDSURFACE
    voxelize: bool = DEFAULT_VOXELIZE
    voxelize_polycount: int = DEFAULT_VOXELIZE_POLYCOUNT  # x1000 polys
    decimate_if_above: bool = DEFAULT_DECIMATE_IF_ABOVE
    decimation_limit: int = DEFAULT_DECIMATION_LIMIT  # x1000 polys
    tangent_smooth: bool = DEFAULT_TANGENT_SMOOTH
    bypass_density_modal: bool = DEFAULT_BYPASS_DENSITY_MODAL
    quality: str = DEFAULT_QUALITY  # "draft", "intermediate", "best"


def configure_autopo(params: AutopoParams) -> None:
    """
    Configure autopo settings before execution.

    This sets all the UI values without executing the command.

    Args:
        params: AutopoParams with all settings
    """
    # Debug: print values being set
    print(f"[Autopo Config] Setting polycount: {params.target_polycount}")
    print(f"[Autopo Config] Setting capture_details: {params.capture_details}")
    print(f"[Autopo Config] Setting auto_density: {params.auto_density}")
    print(f"[Autopo Config] Setting hardsurface: {params.hardsurface}")
    print(f"[Autopo Config] Setting voxelize: {params.voxelize}")
    print(
        f"[Autopo Config] Setting voxelize_polycount: {params.voxelize_polycount}")
    print(
        f"[Autopo Config] Setting decimate_if_above: {params.decimate_if_above}")
    print(
        f"[Autopo Config] Setting decimation_limit: {params.decimation_limit}")
    print(f"[Autopo Config] Setting tangent_smooth: {params.tangent_smooth}")
    print(
        f"[Autopo Config] Setting bypass_density_modal: {params.bypass_density_modal}")
    print(f"[Autopo Config] Setting quality: {params.quality}")

    # Try multiple approaches to set polycount
    # First try setEditBoxValue with int
    r1a: bool = coat.ui.setEditBoxValue(
        SETTING_REQUIRED_POLYCOUNT, int(params.target_polycount))
    print(
        f"[Autopo Config] setEditBoxValue(int) RequiredPolycount returned: {r1a}")

    # Also try setSliderValue (in case it's a slider internally)
    r1b: bool = coat.ui.setSliderValue(
        SETTING_REQUIRED_POLYCOUNT, float(params.target_polycount))
    print(f"[Autopo Config] setSliderValue RequiredPolycount returned: {r1b}")

    # Also try setEditBoxValue with float
    r1c: bool = coat.ui.setEditBoxValue(
        SETTING_REQUIRED_POLYCOUNT, float(params.target_polycount))
    print(
        f"[Autopo Config] setEditBoxValue(float) RequiredPolycount returned: {r1c}")

    # Set slider values
    r2: bool = coat.ui.setSliderValue(
        SETTING_CAPTURE_DETAILS, float(params.capture_details))
    print(f"[Autopo Config] setSliderValue CaptureDetails returned: {r2}")

    r3: bool = coat.ui.setSliderValue(
        SETTING_AUTO_DENSITY, float(params.auto_density))
    print(f"[Autopo Config] setSliderValue AutoDensity returned: {r3}")

    # Set boolean values (verified working methods only)
    r4: bool = coat.ui.setBoolValue(SETTING_HARDSURFACE, params.hardsurface)
    print(f"[Autopo Config] setBoolValue Hardsurface returned: {r4}")

    # VOXELIZE - setBoolValue works (verified)
    r5: bool = coat.ui.setBoolValue(SETTING_VOXELIZE, params.voxelize)
    print(f"[Autopo Config] setBoolValue Voxelize returned: {r5}")

    # VOXELIZE POLYCOUNT - Works when checkbox is enabled first!
    # CRITICAL: Field is hidden until voxelize checkbox is enabled - must wait for UI
    if params.voxelize:
        # Wait 2 frames for voxelize checkbox to enable and show the polycount field
        coat.io.step(2)
        # setEditBoxValue(int) works (verified 2025-02-15)
        r6: bool = coat.ui.setEditBoxValue(
            SETTING_VOXELIZE_POLYCOUNT, int(params.voxelize_polycount))
        print(
            f"[Autopo Config] setEditBoxValue VoxelizePolycount returned: {r6}")

    # DECIMATE IF ABOVE - setBoolValue works (verified)
    r7: bool = coat.ui.setBoolValue(
        SETTING_DECIMATE_IF_ABOVE, params.decimate_if_above)
    print(f"[Autopo Config] setBoolValue DecimateIfAbove returned: {r7}")

    # DECIMATION LIMIT - setEditBoxValue(int) works (verified)
    r8: bool = coat.ui.setEditBoxValue(
        SETTING_DECIMATION_LIMIT, int(params.decimation_limit))
    print(f"[Autopo Config] setEditBoxValue DecimationLimit returned: {r8}")

    # TANGENT SMOOTH - setBoolValue works (verified)
    r9: bool = coat.ui.setBoolValue(
        SETTING_TANGENT_SMOOTH, params.tangent_smooth)
    print(f"[Autopo Config] setBoolValue TangentSmooth returned: {r9}")

    # BYPASS DENSITY MODAL - setBoolValue works (verified)
    r10: bool = coat.ui.setBoolValue(
        SETTING_BYPASS_DENSITY_MODAL, params.bypass_density_modal)
    print(f"[Autopo Config] setBoolValue BypassDensityModal returned: {r10}")

    # QUALITY - Use cmd() which works (verified 2025-02-15)
    # Defensive: handle None or missing quality gracefully
    quality = params.quality if params.quality else "intermediate"
    quality_map = {
        "draft": QUALITY_DRAFT,
        "intermediate": QUALITY_INTERMEDIATE,
        "best": QUALITY_BEST,
    }
    quality_cmd = quality_map.get(quality.lower(), QUALITY_INTERMEDIATE)

    # cmd() works (verified) - setOption() does NOT work
    r11: bool = coat.ui.cmd(quality_cmd)
    print(f"[Autopo Config] cmd(quality={quality}) returned: {r11}")

    # NOTE: Do NOT call coat.ui.apply() here - it simulates Enter key
    # which triggers revoxelize on surface meshes in sculpt room


def create_autopo_configurator(params: AutopoParams) -> Callable[[], None]:
    """
    Create a callback that configures autopo dialog and clicks OK.

    The dialog must be open when this callback runs.

    Args:
        params: AutopoParams with all settings

    Returns:
        Callback function to pass to coat.ui.cmd()
    """
    def configurator() -> None:
        # Wait for dialog to be fully ready
        wait_frames(2)
        # Set all dialog values
        configure_autopo(params)
        # Click OK to execute
        coat.ui.cmd(CMD_DIALOG_OK_LOCAL)
    return configurator


def execute_autopo(params: AutopoParams) -> bool:
    """
    Execute autopo with given parameters.

    Opens the Quadrangulate dialog, configures it with params,
    and clicks OK to start the autopo process.

    Args:
        params: AutopoParams dataclass with all settings

    Returns:
        True if autopo started successfully, False on error
    """
    # NOTE: Do not switch rooms before autopo - it may modify the source mesh
    # Autopo will automatically switch to the appropriate room

    # Validate we have something selected
    current = coat.Scene.current()
    if not current:
        show_error("No object selected for autopo", 3000)
        return False

    # Use a counter to track callback invocations
    # The callback is called each frame while the dialog is open
    _call_count: list[int] = [0]

    def configure_and_confirm() -> None:
        _call_count[0] += 1
        call = _call_count[0]

        if call == 1:
            # First frame: Configure values
            print(
                f"[Autopo] Frame {call}: Configuring dialog with polycount={params.target_polycount}")
            configure_autopo(params)
        elif call == 2:
            # Second frame: Click OK (values should be applied now)
            print(f"[Autopo] Frame {call}: Clicking OK")
            coat.ui.cmd(CMD_DIALOG_OK_LOCAL)
        else:
            # Subsequent frames: Keep clicking OK
            print(f"[Autopo] Frame {call}: Still clicking OK")
            coat.ui.cmd(CMD_DIALOG_OK_LOCAL)

    result: bool = coat.ui.cmd(CMD_AUTOPO, configure_and_confirm)

    if result:
        show_message(
            f"Autopo started (target: {params.target_polycount:,} polys)", 2000)
        # Wait for autopo to complete
        wait_frames(AUTOPO_WAIT_FRAMES)
        # Return to sculpt room
        ensure_sculpt_room()
    else:
        show_error("Failed to start autopo", 3000)

    return result


# =============================================================================
# IMPORT CONFIGURATORS
# =============================================================================

def configure_import_dialog() -> Callable[[], None]:
    """Create a callback to confirm import dialog."""
    def configurator() -> None:
        coat.ui.cmd(CMD_DIALOG_OK)
    return configurator


def import_retopo_to_sculpt() -> bool:
    """
    Import retopo mesh to sculpt room.

    Returns:
        True if successful
    """
    switch_to_room(ROOM_SCULPT, IMPORT_WAIT_FRAMES)
    result: bool = coat.ui.cmd(CMD_RETOPO_TO_SCULPT)
    wait_frames(IMPORT_WAIT_FRAMES)
    ensure_sculpt_room()
    return result


def import_as_multiresolution() -> bool:
    """
    Import retopo mesh as multiresolution lowest level.

    The retopo object name must match the selected sculpt object.
    Running autopo on a sculpt object produces a matching name by default.

    Returns:
        True if successful
    """
    switch_to_room(ROOM_SCULPT, IMPORT_WAIT_FRAMES)
    result: bool = coat.ui.cmd(CMD_IMPORT_MULTIRES)
    wait_frames(IMPORT_WAIT_FRAMES)
    ensure_sculpt_room()
    return result


def clear_retopo_mesh() -> None:
    """Clear all retopo mesh data."""
    switch_to_room(ROOM_RETOPO, IMPORT_WAIT_FRAMES)
    coat.ui.cmd(CMD_CLEAR_RETOPO)
    show_message("Retopo mesh cleared", 2000)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _load_params_from_settings() -> AutopoParams:
    """
    Load AutopoParams from cached LKS settings.

    Returns:
        AutopoParams populated from settings cache
    """
    from ported.utils.lks_settings import get_autopo_settings
    settings = get_autopo_settings()

    return AutopoParams(
        target_polycount=settings.autopo_polycount,
        capture_details=settings.autopo_capture_details,
        auto_density=settings.autopo_auto_density,
        hardsurface=settings.autopo_hardsurface,
        voxelize=settings.autopo_voxelize,
        voxelize_polycount=settings.autopo_voxelize_polycount,
        decimate_if_above=settings.autopo_decimate_if_above,
        decimation_limit=settings.autopo_decimation_limit,
        tangent_smooth=settings.autopo_tangent_smooth,
        bypass_density_modal=settings.autopo_bypass_density_modal,
        # Defensive: handle missing quality in old settings files
        quality=getattr(settings, 'autopo_quality',
                        'intermediate') or 'intermediate',
    )


# =============================================================================
# HIGH-LEVEL WORKFLOW FUNCTIONS
# =============================================================================

def autopo_to_sculpt(params: AutopoParams | None = None) -> bool:
    """
    Run autopo, import result to sculpt, reparent as sibling, and ghost original.

    The imported mesh is reparented to be under the same parent as the original
    object (as a sibling), rather than as a child of the original.

    Args:
        params: AutopoParams (loads from settings if None)

    Returns:
        True if successful, False on error
    """
    if params is None:
        params = _load_params_from_settings()

    # Cache original object info
    current = coat.Scene.current()
    if not current:
        show_error("No object selected", 3000)
        return False

    original_element: coat.SceneElement = current
    original_name: str = original_element.name()
    original_parent: coat.SceneElement = original_element.parent()

    # Run autopo
    if not execute_autopo(params):
        return False

    # Wait for autopo to complete
    wait_frames(AUTOPO_WAIT_FRAMES)

    # Switch to retopo to access the result, then back to sculpt
    switch_to_room(ROOM_RETOPO, IMPORT_WAIT_FRAMES)

    # Import to sculpt
    if not import_retopo_to_sculpt():
        show_error("Failed to import retopo to sculpt", 3000)
        return False

    # Wait for import to complete
    wait_frames(IMPORT_WAIT_FRAMES)

    # Find the newly imported object (it should be the current selection now)
    imported_element: coat.SceneElement = coat.Scene.current()

    # Reparent imported mesh to be sibling of original (under same parent)
    reparented: bool = False
    if imported_element and original_parent:
        try:
            imported_element.changeParent(original_parent)
            reparented = True
        except Exception:
            # changeParent may fail in some cases
            pass

    # Ghost the original object
    try:
        original_element.setGhost(True)
        if reparented:
            show_message(
                f"Imported '{imported_element.name()}' as sibling, ghosted '{original_name}'", 3000)
        else:
            show_message(f"Imported retopo, ghosted '{original_name}'", 3000)
    except Exception:
        show_message("Imported retopo (could not ghost original)", 3000)

    return True


def autopo_to_multiresolution(params: AutopoParams | None = None) -> bool:
    """
    Run autopo and import as multiresolution lowest level.

    Args:
        params: AutopoParams (loads from settings if None)

    Returns:
        True if successful, False on error
    """
    if params is None:
        params = _load_params_from_settings()

    # Run autopo
    if not execute_autopo(params):
        return False

    wait_frames(AUTOPO_WAIT_FRAMES)

    # Import as multiresolution
    if not import_as_multiresolution():
        show_error("Failed to import as multiresolution", 3000)
        return False

    show_message("Imported as multiresolution", 3000)
    return True


# =============================================================================
# CONVENIENCE FUNCTION (for action scripts)
# =============================================================================

def run_autopo_with_settings() -> bool:
    """
    Run autopo using cached LKS settings.

    Reads all autopo parameters from the autopo settings cache.
    """
    params = _load_params_from_settings()
    return execute_autopo(params)
