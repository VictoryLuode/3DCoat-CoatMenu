"""
Export_ScaleSave Operator

Scale objects, export, then restore original scale.

Useful for exporting at different scales without modifying the scene.
"""
from __future__ import annotations

import coat
from ported.utils.scene_api import SceneAPI
from ported.utils.coat_ui_utils import show_message


# =============================================================================
# HELPERS
# =============================================================================

def scale_element(element: coat.SceneElement, scale_factor: float) -> None:
    """Scale an element by the given factor."""
    element.selectOne()
    transform: coat.mat4 = element.getTransform()
    existing_scale: coat.vec3 = transform.GetScaling()
    new_scale = existing_scale * scale_factor
    transform.SetScaling(new_scale)
    element.setTransform(transform)


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scale_up_factor: float = 100.0,
    export_command: str = "$ExportPatternForMerge",
) -> bool:
    """
    Scale up, export, then scale back down.

    Args:
        scale_up_factor: Factor to scale up before export
        export_command: 3DCoat command to run for export

    Returns:
        True if successful
    """
    element: coat.SceneElement | None = SceneAPI.get_current_element()
    if not element:
        show_message("No object selected", 2000)
        return False

    # Scale up
    scale_element(element, scale_up_factor)

    # Export
    coat.ui.cmd(export_command)

    # Scale back down
    scale_element(element, 1.0 / scale_up_factor)

    show_message(f"Exported at {scale_up_factor}x scale", 2000)
    return True
