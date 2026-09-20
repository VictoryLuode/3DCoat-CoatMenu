"""
3DCoat UI Utilities - Abstraction layer for UI commands.

Hides magic strings and provides consistent patterns for
common UI operations like dialogs, room switching, messages.
"""
import coat

# =============================================================================
# MAGIC STRING CONSTANTS
# =============================================================================

# Dialog buttons
CMD_DIALOG_OK: str = "$DialogButton#1"
CMD_DIALOG_CANCEL: str = "$DialogButton#2"

# Room names
ROOM_SCULPT: str = "Sculpt"
ROOM_RETOPO: str = "Retopo"
ROOM_PAINT: str = "Paint"
ROOM_TWEAK: str = "Tweak"
ROOM_UV: str = "UV"
ROOM_RENDER: str = "Render"

# Common commands
CMD_DECIMATE_TO_RETOPO: str = "$DecimateToRetopo"
CMD_DECIMATE_ALL_TO_RETOPO: str = "$DecimateAllToRetopo"
CMD_CLEAR_RETOPO: str = "$ClearTM"
CMD_SNAP_TO_NORMAL: str = "$SnapToNearestAlongNormal"
CMD_APPLY_SMOOTH: str = "$ApplyTSm"
CMD_EXPORT_OBJECT: str = "$EXPORTOBJECT"
CMD_BLENDER_EXPORT: str = "$Blender"

# Autopo commands (see autopo_utils.py for full autopo magic strings)
CMD_AUTOPO: str = "$AutoRetopo"
CMD_RETOPO_TO_SCULPT: str = "$RetopoToSculpt"
CMD_IMPORT_MULTIRES: str = "$AddLowestLevelFromRetopo"

# Baking commands
CMD_BAKE_NORMAL_FLAT_DISP: str = "$MergeForDPNM_flatdisp"

# Freeze/Mask commands
CMD_HIDE_FROZEN_AREA: str = "$HideFrozenArea"
CMD_SEPARATE_HIDDEN: str = "$SeparateHidden"

# Fill/Paint commands
CMD_FILL_LAYER: str = "$FILLLAYER1"
SETTING_PEN_DEPTH: str = "$PEN_DEPTH"

# Smooth commands
CMD_SMOOTH_OBJECT: str = "$SmoothObject"
SETTING_SMOOTH_DEGREE: str = "$SmoothParams::SmoothingDegree"

# Transform commands
CMD_TO_GLOBAL_SPACE: str = "$ToGlobalSpace"
CMD_DECOMPOSE: str = "$Decompose"

# Default timing constants
DEFAULT_WAIT_FRAMES: int = 4
DEFAULT_MESSAGE_DURATION_MS: int = 2000
DEFAULT_ERROR_DURATION_MS: int = 3000


# =============================================================================
# UI FUNCTIONS
# =============================================================================

def confirm_dialog() -> None:
    """Click OK on current dialog."""
    coat.ui.cmd(CMD_DIALOG_OK)


def cancel_dialog() -> None:
    """Click Cancel on current dialog."""
    coat.ui.cmd(CMD_DIALOG_CANCEL)


def command_with_confirm(command: str) -> None:
    """
    Execute command and auto-confirm its dialog.

    Args:
        command: The command to execute (e.g., "$DecimateToRetopo")
    """
    coat.ui.cmd(command, lambda: coat.ui.cmd(CMD_DIALOG_OK))


def execute_command(command: str) -> None:
    """
    Execute a UI command.

    Args:
        command: The command to execute
    """
    coat.ui.cmd(command)


def is_in_room(room: str) -> bool:
    """
    Check if currently in the specified room.

    Uses 'contains' check since currentRoom() may return variations
    like "Sculpt Room" vs "Sculpt".

    Args:
        room: Room name to check for

    Returns:
        True if currently in the specified room
    """
    current_room: str = coat.ui.currentRoom()
    return room in current_room


def switch_to_room(room: str, wait_frames_count: int = DEFAULT_WAIT_FRAMES, force: bool = True, confirm_dialog: bool = True) -> None:
    """
    Switch to specified room and wait for transition.

    If a confirmation dialog appears during room switch, it will be automatically
    confirmed if confirm_dialog is True.

    Args:
        room: Room name ("Sculpt", "Retopo", "Paint", "Tweak", "UV", "Render")
        wait_frames_count: Number of frames to wait after switch (default 4)
        force: Force room switch even if 3DCoat thinks it's not needed (default True)
        confirm_dialog: Auto-confirm any dialogs that appear (default True)
    """
    if not is_in_room(room):
        coat.ui.toRoom(room, force)
        # Auto-confirm any dialog that may have appeared
        if confirm_dialog:
            coat.io.step(1)  # Brief wait for dialog to appear
            coat.ui.cmd(CMD_DIALOG_OK)  # Try to click OK (no-op if no dialog)
        coat.io.step(wait_frames_count)


def get_current_room() -> str:
    """Get the current room name."""
    return coat.ui.currentRoom()


def ensure_sculpt_room(wait_frames: int = DEFAULT_WAIT_FRAMES) -> None:
    """Ensure we're in Sculpt room, switching if needed."""
    switch_to_room(ROOM_SCULPT, wait_frames)


def ensure_retopo_room(wait_frames: int = DEFAULT_WAIT_FRAMES) -> None:
    """Ensure we're in Retopo room, switching if needed."""
    switch_to_room(ROOM_RETOPO, wait_frames)


def ensure_paint_room(wait_frames: int = DEFAULT_WAIT_FRAMES) -> None:
    """Ensure we're in Paint room, switching if needed."""
    switch_to_room(ROOM_PAINT, wait_frames)


def show_message(text: str, duration_ms: int = DEFAULT_MESSAGE_DURATION_MS) -> None:
    """
    Show toast message to user.

    Args:
        text: Message text
        duration_ms: Display duration in milliseconds (default 2000)
    """
    coat.ui.showInfoMessage(text, duration_ms)


def show_error(text: str, duration_ms: int = DEFAULT_ERROR_DURATION_MS) -> None:
    """
    Show error message to user (longer duration).

    Args:
        text: Error message text
        duration_ms: Display duration in milliseconds (default 3000)
    """
    error_text: str = f"Error: {text}"
    coat.ui.showInfoMessage(error_text, duration_ms)


def wait_frames(n: int) -> None:
    """
    Wait for n frames (for async operation completion).

    Args:
        n: Number of frames to wait
    """
    coat.io.step(n)


def set_bool_value(setting: str, value: bool) -> None:
    """
    Set a boolean UI value.

    Args:
        setting: Setting path (e.g., "$SomeSetting")
        value: Boolean value to set
    """
    coat.ui.setBoolValue(setting, value)


def set_editbox_value(setting: str, value: int | float | str) -> None:
    """
    Set an edit box UI value (works for int, float, or str).

    Args:
        setting: Setting path
        value: Value to set (int, float, or str)
    """
    coat.ui.setEditBoxValue(setting, value)


def set_slider_value(setting: str, value: float) -> None:
    """
    Set a slider UI value.

    Args:
        setting: Setting path
        value: Float value to set
    """
    coat.ui.setSliderValue(setting, value)


def get_bool_field(setting: str) -> bool:
    """
    Get a boolean field value.

    Args:
        setting: Setting path

    Returns:
        Current boolean value
    """
    return coat.ui.getBoolField(setting)
