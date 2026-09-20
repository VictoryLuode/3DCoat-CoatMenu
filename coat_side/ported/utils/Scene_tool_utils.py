"""
Scene Tool Utilities - Tool selection and switching for 3DCoat.

Provides utilities for:
- Selecting specific tools (brushes, pens)
- Caching and restoring the current tool
- Ensuring a paint tool is active for layer operations

Usage:
    from ported.utils.Scene_tool_utils import with_paint_tool, select_std_pen
    
    # Ensure StdPen is active for layer operations
    with with_paint_tool():
        consolidate_layers()
    
    # Or manually
    original = get_current_tool()
    select_std_pen()
    do_stuff()
    restore_tool(original)
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import coat


# =============================================================================
# TOOL UI COMMAND CONSTANTS
# =============================================================================

# Paint tools - these are needed for layer operations to work
CMD_STD_PEN: str = "$StdPen"
CMD_AIRBRUSH: str = "$Airbrush"
CMD_FILL_TOOL: str = "$FillTool"
CMD_ERASER: str = "$Eraser"
CMD_LASSO_FILL: str = "$LassoFill"
CMD_RECTANGLE_FILL: str = "$RectangleFill"
CMD_ELLIPSE_FILL: str = "$EllipseFill"
CMD_CONTOUR_FILL: str = "$ContourFill"

# Sculpt tools (sampling - may not work for layer ported.ops)
CMD_CLAY: str = "$Clay"
CMD_CARVE: str = "$Carve"
CMD_BUILD: str = "$Build"
CMD_FLATTEN: str = "$Flatten"
CMD_SMOOTH: str = "$Smooth"

# Tool IDs for coat.IsInTool() - these are the internal identifiers
TOOL_ID_STD_PEN: str = "StdPen"
TOOL_ID_AIRBRUSH: str = "Airbrush"
TOOL_ID_FILL_TOOL: str = "FillTool"
TOOL_ID_ERASER: str = "Eraser"
TOOL_ID_LASSO_FILL: str = "LassoFill"
TOOL_ID_RECTANGLE_FILL: str = "RectangleFill"
TOOL_ID_ELLIPSE_FILL: str = "EllipseFill"
TOOL_ID_CONTOUR_FILL: str = "ContourFill"
TOOL_ID_CLAY: str = "Clay"
TOOL_ID_CARVE: str = "Carve"
TOOL_ID_BUILD: str = "Build"
TOOL_ID_FLATTEN: str = "Flatten"
TOOL_ID_SMOOTH: str = "Smooth"

# Map of tool IDs to their UI commands
TOOL_COMMANDS: dict[str, str] = {
    TOOL_ID_STD_PEN: CMD_STD_PEN,
    TOOL_ID_AIRBRUSH: CMD_AIRBRUSH,
    TOOL_ID_FILL_TOOL: CMD_FILL_TOOL,
    TOOL_ID_ERASER: CMD_ERASER,
    TOOL_ID_LASSO_FILL: CMD_LASSO_FILL,
    TOOL_ID_RECTANGLE_FILL: CMD_RECTANGLE_FILL,
    TOOL_ID_ELLIPSE_FILL: CMD_ELLIPSE_FILL,
    TOOL_ID_CONTOUR_FILL: CMD_CONTOUR_FILL,
    TOOL_ID_CLAY: CMD_CLAY,
    TOOL_ID_CARVE: CMD_CARVE,
    TOOL_ID_BUILD: CMD_BUILD,
    TOOL_ID_FLATTEN: CMD_FLATTEN,
    TOOL_ID_SMOOTH: CMD_SMOOTH,
}

# Paint tools that work with layer operations
PAINT_TOOL_IDS: list[str] = [
    TOOL_ID_STD_PEN,
    TOOL_ID_AIRBRUSH,
    TOOL_ID_FILL_TOOL,
    TOOL_ID_ERASER,
    TOOL_ID_LASSO_FILL,
    TOOL_ID_RECTANGLE_FILL,
    TOOL_ID_ELLIPSE_FILL,
    TOOL_ID_CONTOUR_FILL,
]

# All known tool IDs for probing
ALL_TOOL_IDS: list[str] = list(TOOL_COMMANDS.keys())


# =============================================================================
# TOOL DETECTION
# =============================================================================

def get_current_tool() -> str | None:
    """
    Get the currently active tool ID by probing known tools.

    Returns the tool ID string if found, or None if no known tool is active.

    Note: This probes tools one by one using coat.IsInTool() which is slow
    but the only reliable way to detect the current tool.
    """
    for tool_id in ALL_TOOL_IDS:
        if coat.IsInTool(tool_id):
            return tool_id
    return None


def is_paint_tool_active() -> bool:
    """Check if a paint tool (one that works with layer ported.ops) is active."""
    for tool_id in PAINT_TOOL_IDS:
        if coat.IsInTool(tool_id):
            return True
    return False


# =============================================================================
# TOOL SELECTION
# =============================================================================


def select_tool(tool_id: str) -> bool:
    """
    Select a tool by its ID.

    Args:
        tool_id: The tool identifier (e.g., "StdPen", "Clay")

    Returns:
        True if the tool command was found and executed, False otherwise.
    """
    cmd: str | None = TOOL_COMMANDS.get(tool_id)
    if cmd:
        coat.ui.cmd(cmd)
        return True
    return False


def select_std_pen() -> None:
    """Select the StdPen paint tool."""
    coat.ui.cmd(CMD_STD_PEN)


def restore_tool(tool_id: str | None) -> None:
    """
    Restore a previously cached tool.

    Args:
        tool_id: The tool ID to restore, or None to do nothing.
    """
    if tool_id is not None:
        select_tool(tool_id)

# =============================================================================
# CONTEXT MANAGER FOR TOOL SWITCHING
# =============================================================================


@contextmanager
def with_paint_tool(preferred_tool: str = TOOL_ID_STD_PEN) -> Iterator[None]:
    """
    Context manager that ensures a paint tool is active for the duration.

    If a paint tool is already active, it stays active (no switch).
    Otherwise, switches to the preferred tool and restores the original after.

    Usage:
        with with_paint_tool():
            # Layer operations that require a paint tool
            merge_layer_up()
            duplicate_current_layer()

    Args:
        preferred_tool: Tool to switch to if no paint tool is active.
                       Defaults to StdPen.
    """
    original_tool: str | None = None
    switched: bool = False

    # Check if we already have a paint tool active
    if not is_paint_tool_active():
        # Cache current tool and switch
        original_tool = get_current_tool()
        select_tool(preferred_tool)
        switched = True

    try:
        yield
    finally:
        # Restore original tool if we switched
        if switched and original_tool is not None:
            restore_tool(original_tool)


@contextmanager
def with_tool(tool_id: str) -> Iterator[None]:
    """
    Context manager that switches to a specific tool and restores after.

    Always switches to the specified tool, regardless of current state.

    Usage:
        with with_tool(TOOL_ID_CLAY):
            # Do something with Clay tool
            pass

    Args:
        tool_id: The tool to switch to.
    """
    original_tool: str | None = get_current_tool()

    if original_tool != tool_id:
        select_tool(tool_id)

    try:
        yield
    finally:
        if original_tool is not None and original_tool != tool_id:
            restore_tool(original_tool)
