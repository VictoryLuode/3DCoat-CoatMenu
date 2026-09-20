"""
SculptObject_IdColors Operator

Fill sculpt objects with random ID colors for texture baking.
Each object gets a unique random color on the IDMap layer.

Uses ghost isolation pattern to ensure fill only affects one object at a time.
"""
import coat
import random
from pathlib import Path
from datetime import datetime
from typing import Callable
from ported.utils.scene_api import SceneAPI, get_element_path
from ported.utils.scope_utils import Scope, resolve_scope
from ported.utils.coat_ui_utils import (
    CMD_FILL_LAYER,
    SETTING_PEN_DEPTH,
    show_message,
    show_error,
    wait_frames,
)
from ported.utils.SceneElement_visibility_utils import (
    cache_ghost_states,
    restore_ghost_states,
    ghost_elements,
)


# =============================================================================
# DEBUG MODE - set to True to enable debug output to file
# =============================================================================

DEBUG_MODE: bool = True
DEBUG_LOG_PATH: Path = Path(__file__).parent.parent / \
    "data" / "idcolors_debug.log"


def _debug_log(message: str) -> None:
    """Write debug message to log file."""
    if not DEBUG_MODE:
        return
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            timestamp: str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Ignore logging errors


def _debug_clear() -> None:
    """Clear the debug log file."""
    if not DEBUG_MODE:
        return
    try:
        with open(DEBUG_LOG_PATH, "w", encoding="utf-8") as f:
            f.write(
                f"=== IdColors Debug Log - {datetime.now().isoformat()} ===\n\n")
    except Exception:
        pass

# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================


DEFAULT_LAYER_NAME: str = "IDMap"
DEFAULT_MIN_COLOR: int = 0


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _fill_element_with_random_color(
    element: coat.SceneElement,
    min_color: int = DEFAULT_MIN_COLOR
) -> None:
    """Fill a single element with a random RGB color using ghost isolation."""
    # Unghost this element, fill, re-ghost
    element.setGhost(False)

    # Generate random color
    r: float = random.uniform(min_color, 255)
    g: float = random.uniform(min_color, 255)
    b: float = random.uniform(min_color, 255)

    coat.Volume.color(r, g, b)
    coat.ui.cmd(CMD_FILL_LAYER)
    wait_frames(5)

    # Re-ghost so next element can be filled in isolation
    element.setGhost(True)


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.TREE,
    layer_name: str = DEFAULT_LAYER_NAME,
    min_color: int = DEFAULT_MIN_COLOR,
    restore_layer: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Fill objects with random ID colors.

    Args:
        scope: Which objects to fill (TREE = selected + children, ALL = everything)
        layer_name: Name of the layer to create/use for ID colors
        min_color: Minimum RGB value (0-255) to avoid pure black
        restore_layer: Whether to restore Layer 0 as active after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects filled
    """
    # Get current element for reference (needed for TREE scope and selection restore)
    active_element: coat.SceneElement | None = SceneAPI.get_current_element()

    # DEBUG: Clear and start new log session
    if DEBUG_MODE:
        _debug_clear()
        _debug_log(f"=== ID Colors Operation Started ===")
        _debug_log(f"Scope: {scope}")
        _debug_log(
            f"Active element: {active_element.name() if active_element else 'None'}")

    if not active_element and scope == Scope.TREE:
        show_error("No object selected", 2000)
        return 0

    # Resolve which elements to operate on
    elements: list[coat.SceneElement] = resolve_scope(scope)

    # DEBUG: Log all resolved elements with their paths
    if DEBUG_MODE:
        _debug_log(
            f"\n=== resolve_scope() returned {len(elements)} elements ===")
        for i, el in enumerate(elements):
            path: str = get_element_path(el)
            name: str = el.name() if el else "?"
            is_sculpt: bool = el.isSculptObject() if el else False
            py_id: int = id(el)
            _debug_log(
                f"  [{i:3d}] name={name:<20} sculpt={is_sculpt}  id={py_id}  path={path}")

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    # Save original pen depth
    original_pen_depth: float = coat.ui.getSliderValue(SETTING_PEN_DEPTH)

    # Set pen depth to 0 for color-only filling
    coat.ui.setSliderValue(SETTING_PEN_DEPTH, 0)

    # Switch to IDMap layer (creates if not exists)
    layer_id: int = coat.Scene.getLayer(layer_name, True)
    coat.Scene.setActiveLayer(layer_id)
    coat.Scene.setLayerDepthOpacity(layer_id, 0)

    # Collect ALL scene elements for ghost management
    all_elements: list[coat.SceneElement] = SceneAPI.collect_all_sculpt_objects()

    # DEBUG: Log all scene elements
    if DEBUG_MODE:
        _debug_log(
            f"\n=== collect_all_sculpt_objects() returned {len(all_elements)} elements ===")
        for i, el in enumerate(all_elements):
            path: str = get_element_path(el)
            name: str = el.name() if el else "?"
            py_id: int = id(el)
            _debug_log(f"  [{i:3d}] name={name:<20} id={py_id}  path={path}")

    # Cache ghost states for restoration
    ghost_cache: dict[int, bool] = cache_ghost_states(all_elements)

    # Ghost everything in the scene
    ghost_elements(all_elements)

    # Fill each element (unghost one at a time)
    count: int = 0
    sculpt_count: int = 0

    if DEBUG_MODE:
        _debug_log(f"\n=== Fill Loop ===")

    total: int = len(elements)
    sculpt_count: int = 0

    for i, el in enumerate(elements):
        if el.isSculptObject():
            if progress_callback is not None:
                progress_callback(sculpt_count, total, el.name())
            sculpt_count += 1
            if DEBUG_MODE:
                path: str = get_element_path(el)
                py_id: int = id(el)
                _debug_log(
                    f"  Fill #{sculpt_count}: {el.name()} id={py_id} path={path}")
            _fill_element_with_random_color(el, min_color)
            count += 1

    # DEBUG: Summary
    if DEBUG_MODE:
        _debug_log(f"\n=== Summary ===")
        _debug_log(f"Total elements in loop: {len(elements)}")
        _debug_log(f"Sculpt objects filled: {count}")
        _debug_log(f"Log file: {DEBUG_LOG_PATH}")
        show_message(f"Debug log: {DEBUG_LOG_PATH.name}", 3000)

    # Restore original ghost states
    restore_ghost_states(all_elements, ghost_cache)

    # Restore original selection
    if active_element:
        active_element.selectOne()

    # Restore layer and pen depth
    if restore_layer:
        coat.Scene.setActiveLayer(coat.Scene.getLayer("Layer 0", True))
    coat.ui.setSliderValue(SETTING_PEN_DEPTH, original_pen_depth)

    show_message(f"Filled {count} objects with ID colors", 2000)
    return count
