"""
Layer Management Utilities

Provides utilities for managing sculpt layers in 3DCoat.

Standard Layer Contract (from design):
- Layer 0: Sculpt detail (100% Depth, 0% Color)
- Layer1: Color/material (0% Depth, 100% Color; 3DCoat paint default name)

Known Gotchas:
- Decimate and other operations auto-create layers
- Layer order is not guaranteed after operations
- Duplicate names are allowed
- Layer indices can shift

CRITICAL API LIMITATION:
3DCoat's layer API implicitly creates layers when querying non-existent IDs:
- getLayerName(id), layerVisible(id), layerIsEmpty(id) all CREATE layers
- There is no getLayersCount() or safe enumeration method
- getLayer(name) requires knowing the name ahead of time

Safe Layer Operations:
- Layer 0 always exists
- getCurrentLayer() returns a valid layer ID
- Use UI commands for layer manipulation (slow but safe)

Verified API (from coat.pyi - all on coat.Scene):
- getLayer(name, addIfNotExists=True) -> int
- getLayerName(LayerID) -> str
- setLayerName(LayerID, name)
- getCurrentLayer() -> int
- setCurrentLayer(LayerID)
- setActiveLayer(LayerID)
- removeLayer(LayerID)
- removeEmptyLayers()
- layerIsEmpty(layerID) -> bool
- layerVisible(LayerID) -> bool
- setLayerVisibility(LayerID, Visible)
- setLayerColorOpacity(LayerID, Opacity: float)
- setLayerDepthOpacity(LayerID, Opacity: float)
- setLayerGlossOpacity(LayerID, Opacity: float)
- setLayerMetalnessOpacity(LayerID, Opacity: float)
- mergeVisibleLayers()
- mergeLayerDown(LayerID)
"""
import coat


# =============================================================================
# CONSTANTS
# =============================================================================

# Standard layer names — match 3DCoat paint-tool defaults (no space).
# Paint tools auto-create "Layer1"; using "Layer 1" caused a duplicate.
LAYER_SCULPT: str = "Layer 0"  # Layer 0 - depth only
LAYER_COLOR: str = "Layer1"    # Color layer (3DCoat default name)
LAYER_COLOR_LEGACY: str = "Layer 1"  # Pre-alignment name; renamed on setup

# Opacity values
OPACITY_FULL: float = 1.0
OPACITY_NONE: float = 0.0

# Maximum number of layers in 3DCoat
MAX_LAYERS: int = 100


# =============================================================================
# UI COMMAND CONSTANTS (for workarounds when API is insufficient)
# =============================================================================

# These UI commands are discovered experimentally and may change between versions.
# Use these for layer operations that cannot be done safely via API.

# Layer creation
CMD_ADD_NEW_LAYER: str = "$LayersPanel::AddNewLayer"
CMD_ADD_FOLDER: str = "$LayersPanel::AddLFolder"
CMD_ADD_LAYER_MASK: str = "$LayersPanel::AddLayerMask"
CMD_DUPLICATE_LAYER: str = "$LayersPanel::DuplicateLayer"

# Layer merging
CMD_MERGE_DOWN: str = "$LayersPanel::MergeDown"  # Also: $MERGE_DOWN
CMD_MERGE_UP: str = "$MERGE_UP"
CMD_MERGE_VISIBLE: str = "$MERGE_VISIBLE"

# Layer ordering
CMD_MOVE_LAYER_UP: str = "$LayersPanel::MoveLayerUp"
CMD_MOVE_LAYER_DOWN: str = "$LayersPanel::MoveLayerDown"

# Layer deletion
CMD_DELETE_LAYER: str = "$LayersPanel::DeleteLayer"  # Clears contents, keeps layer
CMD_TRASH_LAYER: str = "$LayersPanel::TrashLayer"    # Deletes the layer entirely

# Layer fill
CMD_FILL_LAYER: str = "$FILLLAYER1"  # Fill visible/unghosted with brush


# =============================================================================
# SIMPLE LAYER SETUP (uses API - may create extra layers if state is unknown)
# =============================================================================

def _ensure_color_layer() -> int:
    """
    Return the standard color layer ID, creating or renaming as needed.

    Prefers existing "Layer1". If only legacy "Layer 1" exists, renames it.
    Otherwise creates "Layer1".
    """
    color_layer: int = coat.Scene.getLayer(LAYER_COLOR, False)
    if color_layer >= 0:
        return color_layer

    legacy_layer: int = coat.Scene.getLayer(LAYER_COLOR_LEGACY, False)
    if legacy_layer >= 0:
        coat.Scene.setLayerName(legacy_layer, LAYER_COLOR)
        return legacy_layer

    return coat.Scene.getLayer(LAYER_COLOR, True)


def ensure_standard_layers_simple() -> None:
    """
    Simple layer setup using API calls.

    WARNING: This uses API calls that may create layers if queried IDs don't exist.
    Only use this if you know the scene is in a clean state.

    For unknown/messy layer states, use consolidate_layers() instead.
    """
    # Remove any empty layers first
    coat.Scene.removeEmptyLayers()

    # Configure Layer 0 (Sculpt) - depth only
    # Layer 0 always exists, safe to configure
    coat.Scene.setLayerName(0, LAYER_SCULPT)
    coat.Scene.setLayerDepthOpacity(0, OPACITY_FULL)
    coat.Scene.setLayerColorOpacity(0, OPACITY_NONE)
    coat.Scene.setLayerGlossOpacity(0, OPACITY_NONE)
    coat.Scene.setLayerMetalnessOpacity(0, OPACITY_NONE)

    # Get or create the Color layer (reuse legacy "Layer 1" if present)
    color_layer: int = _ensure_color_layer()

    # Configure color layer - color only
    coat.Scene.setLayerDepthOpacity(color_layer, OPACITY_NONE)
    coat.Scene.setLayerColorOpacity(color_layer, OPACITY_FULL)
    coat.Scene.setLayerGlossOpacity(color_layer, OPACITY_FULL)
    coat.Scene.setLayerMetalnessOpacity(color_layer, OPACITY_FULL)

    # Activate the sculpt layer
    coat.Scene.setActiveLayer(0)
    coat.Scene.setCurrentLayer(0)


# Alias for backwards compatibility
ensure_standard_layers = ensure_standard_layers_simple


def activate_sculpt_layer() -> None:
    """Activate Layer 0 (Sculpt layer) for sculpting."""
    sculpt_layer: int = coat.Scene.getLayer(LAYER_SCULPT, True)
    coat.Scene.setActiveLayer(sculpt_layer)
    coat.Scene.setCurrentLayer(sculpt_layer)


def activate_color_layer() -> None:
    """Activate Layer1 (Color layer) for painting."""
    color_layer: int = coat.Scene.getLayer(LAYER_COLOR, True)
    coat.Scene.setActiveLayer(color_layer)
    coat.Scene.setCurrentLayer(color_layer)


def cleanup_after_destructive_op() -> None:
    """
    Clean up layer state after a destructive operation (decimate, etc).

    Many operations create unwanted layers. This does a lightweight cleanup:
    1. Removes empty layers
    2. Activates layer 0 (guaranteed to exist)

    For a full layer consolidation, use consolidate_layers() instead.
    """
    # Remove empty layers that were created
    coat.Scene.removeEmptyLayers()

    # Activate layer 0 (always safe)
    coat.Scene.setActiveLayer(0)
    coat.Scene.setCurrentLayer(0)


def get_current_layer_name() -> str:
    """Get the name of the currently active layer."""
    layer_id: int = coat.Scene.getCurrentLayer()
    return coat.Scene.getLayerName(layer_id)


def set_layer_depth_only(layer_name: str) -> None:
    """Configure a layer for depth-only (sculpting)."""
    layer_id: int = coat.Scene.getLayer(layer_name, False)
    if layer_id >= 0:
        coat.Scene.setLayerDepthOpacity(layer_id, OPACITY_FULL)
        coat.Scene.setLayerColorOpacity(layer_id, OPACITY_NONE)
        coat.Scene.setLayerGlossOpacity(layer_id, OPACITY_NONE)
        coat.Scene.setLayerMetalnessOpacity(layer_id, OPACITY_NONE)


def set_layer_color_only(layer_name: str) -> None:
    """Configure a layer for color-only (painting)."""
    layer_id: int = coat.Scene.getLayer(layer_name, False)
    if layer_id >= 0:
        coat.Scene.setLayerDepthOpacity(layer_id, OPACITY_NONE)
        coat.Scene.setLayerColorOpacity(layer_id, OPACITY_FULL)
        coat.Scene.setLayerGlossOpacity(layer_id, OPACITY_FULL)
        coat.Scene.setLayerMetalnessOpacity(layer_id, OPACITY_FULL)


def remove_layer_by_name(layer_name: str) -> bool:
    """
    Remove a layer by name.

    Returns True if layer was found and removed.
    """
    layer_id: int = coat.Scene.getLayer(layer_name, False)
    if layer_id >= 0:
        coat.Scene.removeLayer(layer_id)
        return True
    return False


def merge_all_visible() -> None:
    """Merge all visible layers into one."""
    coat.Scene.mergeVisibleLayers()


# =============================================================================
# UI COMMAND HELPERS (slow but safe)
# =============================================================================

def _wait(frames: int = 1) -> None:
    """Wait for UI to settle after a command."""
    coat.io.step(frames)


def add_new_layer() -> int:
    """
    Add a new layer above the current layer using UI command.

    The new layer becomes active. Returns the new layer's ID.

    Note: This uses a UI command because the API's getLayer() with
    addIfNotExists=True doesn't give us control over layer position.
    """
    coat.ui.cmd(CMD_ADD_NEW_LAYER)
    return coat.Scene.getCurrentLayer()


def duplicate_current_layer() -> int:
    """
    Duplicate the current layer using UI command.

    The duplicate appears above the current layer but does NOT become active.
    Returns the current layer ID (not the duplicate).

    Note: We cannot directly get the duplicate's ID without probing,
    which would create layers. Caller must use getLayer(name) if they
    know the duplicate's name pattern ("<original> copy").
    """
    coat.ui.cmd(CMD_DUPLICATE_LAYER)
    return coat.Scene.getCurrentLayer()


def merge_layer_up() -> None:
    """Merge current layer UP into the layer above using UI command."""
    coat.ui.cmd(CMD_MERGE_UP)
    # No wait - batch merges don't need per-op delay


def merge_layer_down() -> None:
    """Merge current layer DOWN into the layer below using UI command."""
    coat.ui.cmd(CMD_MERGE_DOWN)
    # No wait - caller should wait after batch operations


def move_layer_up() -> None:
    """Move current layer up one position using UI command."""
    coat.ui.cmd(CMD_MOVE_LAYER_UP)
    # No wait - batch moves don't need per-op delay


def move_layer_down() -> None:
    """Move current layer down one position using UI command."""
    coat.ui.cmd(CMD_MOVE_LAYER_DOWN)
    # No wait - batch moves don't need per-op delay


def trash_current_layer() -> None:
    """Delete the current layer entirely using UI command."""
    coat.ui.cmd(CMD_TRASH_LAYER)


def move_layer_to_bottom() -> None:
    """Move current layer to the bottom of the stack.

    Uses repeated MoveLayerDown commands. Safe because we don't query
    layer count - we just keep moving down until it stops having effect.
    """
    for _ in range(MAX_LAYERS):
        move_layer_down()


def move_layer_to_top() -> None:
    """Move current layer to the top of the stack.

    Uses repeated MoveLayerUp commands. Safe because we don't query
    layer count - we just keep moving up until it stops having effect.
    """
    for _ in range(MAX_LAYERS):
        move_layer_up()


# =============================================================================
# CONSOLIDATE LAYERS ALGORITHM
# =============================================================================

def consolidate_layers() -> None:
    """
    Consolidate all layers into a standard 2-layer setup:
    - Layer 0 (Sculpt): 100% Depth, 0% Color
    - Layer1 (Color): 0% Depth, 100% Color

    ALGORITHM RATIONALE:
    ---------------------
    3DCoat's layer API is fundamentally broken for enumeration:
    - getLayerName(id), layerVisible(id), layerIsEmpty(id) all CREATE layers
    - There is no getLayersCount() method
    - getLayer(name) requires knowing the name ahead of time

    MERGE STRATEGY:
    - We merge UP (not down) because Layer 0 cannot hold color data
    - Merging down to Layer 0 loses all vertex color information
    - Final merge to Layer 0 is done on a duplicate, immediately before
      setting its opacity to 0% color

    REQUIRES:
    - A paint tool must be active for layer merge commands to work
    - This function automatically switches to StdPen if needed

    STEPS:
    1. Ensure paint tool is active (switch to StdPen if needed)
    2. Activate Layer 0, create accumulator layer above it
    3. Merge UP repeatedly to gather all layers above into accumulator
    4. Duplicate accumulator (preserves color data)
    5. Merge accumulator down into Layer 0 (depth only - color lost)
    6. Rename the copy to "Layer1" and configure opacities
    7. Clean up any leftover layers
    8. Restore original tool if we switched
    """
    # Import here to avoid circular dependency
    from ported.utils.Scene_tool_utils import with_paint_tool

    # Wrap the entire operation in paint tool context
    with with_paint_tool():
        _do_consolidate_layers()


def _do_consolidate_layers() -> None:
    """Internal implementation of consolidate_layers (called within paint tool context)."""
    # Step 1: Activate Layer 0 (guaranteed to exist) and name it
    coat.Scene.setActiveLayer(0)
    coat.Scene.setCurrentLayer(0)
    coat.Scene.setLayerName(0, LAYER_SCULPT)

    # Step 2: Create a new layer (will spawn above Layer 0 and become active)
    new_layer_id: int = add_new_layer()
    accumulator_name: str = "_LKS_Merge_Temp"
    coat.Scene.setLayerName(new_layer_id, accumulator_name)

    # Step 3: Merge UP repeatedly to accumulate all layers above
    # We don't know how many layers exist, but max is 100
    # No per-op wait - fire them all rapidly
    for _ in range(MAX_LAYERS - 1):
        merge_layer_up()

    # Single wait after batch merge operations
    _wait(2)

    # Now we have: Layer 0, Accumulator (with all paint+depth from above)

    # Step 4: Duplicate the accumulator layer
    # The duplicate will be named "_LKS_Merge_Temp copy" and appear above
    duplicate_current_layer()

    # The current layer is still the accumulator (not the copy)
    # Step 5: Merge the accumulator DOWN into Layer 0
    # This merges depth into Layer 0, color is lost (but we have the copy above)
    merge_layer_down()
    _wait(2)

    # Now we have: Layer 0 (with merged depth), and the copy layer above it
    # The copy should now be the current layer after merge down

    # Step 6: Configure the final layer setup
    # Layer 0 - depth only
    coat.Scene.setLayerDepthOpacity(0, OPACITY_FULL)
    coat.Scene.setLayerColorOpacity(0, OPACITY_NONE)
    coat.Scene.setLayerGlossOpacity(0, OPACITY_NONE)
    coat.Scene.setLayerMetalnessOpacity(0, OPACITY_NONE)
    coat.Scene.setLayerName(0, LAYER_SCULPT)

    # Get the copy layer - it should be the current layer now (after merge down)
    # Or we can get it by name pattern
    copy_name: str = f"{accumulator_name} copy"
    copy_layer_id: int = coat.Scene.getLayer(copy_name, False)

    if copy_layer_id >= 0:
        # Rename to standard name and configure as color-only
        coat.Scene.setLayerName(copy_layer_id, LAYER_COLOR)
        coat.Scene.setLayerDepthOpacity(copy_layer_id, OPACITY_NONE)
        coat.Scene.setLayerColorOpacity(copy_layer_id, OPACITY_FULL)
        coat.Scene.setLayerGlossOpacity(copy_layer_id, OPACITY_FULL)
        coat.Scene.setLayerMetalnessOpacity(copy_layer_id, OPACITY_FULL)
    else:
        # Fallback: current layer should be the copy
        current_id: int = coat.Scene.getCurrentLayer()
        if current_id != 0:
            coat.Scene.setLayerName(current_id, LAYER_COLOR)
            coat.Scene.setLayerDepthOpacity(current_id, OPACITY_NONE)
            coat.Scene.setLayerColorOpacity(current_id, OPACITY_FULL)
            coat.Scene.setLayerGlossOpacity(current_id, OPACITY_FULL)
            coat.Scene.setLayerMetalnessOpacity(current_id, OPACITY_FULL)

    # Clean up any empty layers that might remain
    coat.Scene.removeEmptyLayers()

    # Activate the sculpt layer
    coat.Scene.setActiveLayer(0)
    coat.Scene.setCurrentLayer(0)
