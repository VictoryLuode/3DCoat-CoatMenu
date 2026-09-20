"""
Scene Cleanup Utilities - Cleanup after mesh operations.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
"""
import coat


# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

def cleanup_after_mesh_operation() -> None:
    """
    Clean up after destructive mesh operations.

    Mesh operations like decimate often create unwanted layers.
    This removes empty layers and selects layer 0 (active + current).
    """
    coat.Scene.removeEmptyLayers()
    activate_layer_zero()


def remove_empty_layers() -> None:
    """Remove all empty layers from the scene."""
    coat.Scene.removeEmptyLayers()


def activate_layer_zero() -> None:
    """Select layer 0 as both active and current (default sculpt layer)."""
    coat.Scene.setActiveLayer(0)
    coat.Scene.setCurrentLayer(0)
