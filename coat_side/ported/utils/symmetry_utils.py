"""
Symmetry Utilities - coat.symm API wrappers and symmetry operations.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Operators in `ported.ops/` own Config dataclasses and call these functions.

Uses the `coat.symm` Python API (documented in Core API but absent from local
coat.pyi) for direct symmetry plane manipulation.

Axis state is read live via coat.symm.x() / .y() / .z() - no caching, no
persistence. The only persisted symmetry setting is show_symmetry_plane
(in LKS settings, applied via _sync_show_plane_from_settings).
"""
import coat

from ported.utils.coat_ui_utils import wait_frames, show_message, show_error
from ported.utils.lks_settings import get_settings, save_settings

# =============================================================================
# MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

CMD_MAKE_SYMMETRICAL: str = "$MakeSymm"
CMD_SYMMETRY: str = "$SYMMETRY"
CMD_PICK_FROM_BB: str = "$SymmetryParams::PickFromBB"
CMD_RESET_SYMM: str = "$SymmetryParams::ResetSymm"

# =============================================================================
# DEFAULTS
# =============================================================================

MESH_OP_WAIT_FRAMES: int = 2
SYMMETRY_PANE_WAIT_FRAMES: int = 2


# =============================================================================
# coat.symm API WRAPPERS (Core API - NOT in local coat.pyi)
# =============================================================================

def enable_symmetry(enable: bool = True) -> None:
    """Enable or disable symmetry via coat.symm API."""
    coat.symm.enable(enable)
    _sync_show_plane_from_settings()


def is_symmetry_enabled() -> bool:
    """Check if symmetry is currently enabled."""
    return coat.symm.enabled()


def disable_symmetry() -> None:
    """Disable symmetry via coat.symm API."""
    coat.symm.disable()


def toggle_symmetry() -> bool:
    """
    Toggle symmetry on/off. Returns the new state.
    """
    new_state: bool = not coat.symm.enabled()
    coat.symm.enable(new_state)
    _sync_show_plane_from_settings()
    show_message(f"Symmetry {'ON' if new_state else 'OFF'}", 1500)
    return new_state


def set_mirror_axes(x: bool, y: bool, z: bool) -> None:
    """Set which axes are mirrored via coat.symm API."""
    coat.symm.xyz(x, y, z)
    _sync_show_plane_from_settings()


def toggle_mirror_axis(axis: str) -> bool:
    """
    Toggle mirror for a single axis on/off.

    Reads live state from coat.symm.x()/.y()/.z(), flips ONLY the target
    axis, preserves the other two. Does NOT execute $MakeSymm.

    Returns True if the axis was valid.
    """
    axis_upper: str = axis.upper()
    if axis_upper not in ("X", "Y", "Z"):
        show_error(f"Invalid mirror axis: {axis} (must be X, Y, or Z)", 3000)
        return False

    # Read live axis state directly from coat.symm
    x_current: bool = coat.symm.x()
    y_current: bool = coat.symm.y()
    z_current: bool = coat.symm.z()

    # Toggle the target axis only
    if axis_upper == "X":
        new_x: bool = not x_current
        new_y: bool = y_current
        new_z: bool = z_current
    elif axis_upper == "Y":
        new_x = x_current
        new_y = not y_current
        new_z = z_current
    else:
        new_x = x_current
        new_y = y_current
        new_z = not z_current

    # Apply
    coat.symm.xyz(new_x, new_y, new_z)
    any_on: bool = new_x or new_y or new_z
    coat.symm.enable(any_on)

    # Sync show-plane from persisted settings
    _sync_show_plane_from_settings()

    # Feedback
    labels: list[str] = []
    if new_x:
        labels.append("X")
    if new_y:
        labels.append("Y")
    if new_z:
        labels.append("Z")
    state_str: str = ",".join(labels) if labels else "OFF"
    show_message(f"Mirror {state_str}", 1500)
    return True


def show_symmetry_plane(show: bool) -> None:
    """Show or hide the symmetry plane. Persists to LKS settings."""
    coat.symm.showSymmetryPlane(show)
    settings = get_settings()
    settings.show_symmetry_plane = show
    save_settings()


def toggle_show_symmetry_plane() -> bool:
    """Toggle symmetry plane visibility. Returns new state."""
    settings = get_settings()
    current: bool = settings.show_symmetry_plane
    new_state: bool = not current
    coat.symm.showSymmetryPlane(new_state)
    settings.show_symmetry_plane = new_state
    save_settings()
    show_message(f"Symmetry plane {'SHOWN' if new_state else 'HIDDEN'}", 1500)
    return new_state


def make_symmetrical() -> None:
    """Make the current Volume symmetrical (thin wrap of $MakeSymm)."""
    coat.ui.cmd(CMD_MAKE_SYMMETRICAL)
    wait_frames(MESH_OP_WAIT_FRAMES)
    _sync_show_plane_from_settings()


def pick_symmetry_from_bbox() -> None:
    """
    Set symmetry origin to the selected object's bounding-box center.

    `$SYMMETRY` is a pane toggle, not a dialog — callbacks never run. Open the
    pane first (same pattern as Scene_tiling_utils), then invoke PickFromBB.
    """
    coat.ui.cmd(CMD_SYMMETRY)
    wait_frames(SYMMETRY_PANE_WAIT_FRAMES)
    pick_ok: bool = bool(coat.ui.cmd(CMD_PICK_FROM_BB))

    # $SYMMETRY toggles — if pane was already open, first call closed it
    if not pick_ok:
        coat.ui.cmd(CMD_SYMMETRY)
        wait_frames(SYMMETRY_PANE_WAIT_FRAMES)
        coat.ui.cmd(CMD_PICK_FROM_BB)

    _sync_show_plane_from_settings()
    show_message("Symmetry pivot → object BB", 1500)


def reset_symmetry_origin_to_world() -> None:
    """
    Reset symmetry origin to world center, preserving active mirror axes.

    `$SYMMETRY` is a pane toggle (callbacks never run). Open pane, ResetSymm,
    then restore axes — ResetSymm clears all axes / disables symmetry.
    """
    x_on: bool = coat.symm.x()
    y_on: bool = coat.symm.y()
    z_on: bool = coat.symm.z()
    was_enabled: bool = coat.symm.enabled()

    coat.ui.cmd(CMD_SYMMETRY)
    wait_frames(SYMMETRY_PANE_WAIT_FRAMES)
    reset_ok: bool = bool(coat.ui.cmd(CMD_RESET_SYMM))

    if not reset_ok:
        coat.ui.cmd(CMD_SYMMETRY)
        wait_frames(SYMMETRY_PANE_WAIT_FRAMES)
        coat.ui.cmd(CMD_RESET_SYMM)

    coat.symm.xyz(x_on, y_on, z_on)
    if was_enabled or x_on or y_on or z_on:
        coat.symm.enable(True)
    else:
        coat.symm.enable(False)
    _sync_show_plane_from_settings()
    show_message("Symmetry pivot → world", 1500)


# =============================================================================
# INTERNAL
# =============================================================================

def _sync_show_plane_from_settings() -> None:
    """Re-apply persisted show-plane preference to active object."""
    coat.symm.showSymmetryPlane(get_settings().show_symmetry_plane)
