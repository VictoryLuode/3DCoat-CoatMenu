"""
SculptObject_Mirror Operator - Toggle mirror axis on/off.

Toggles the symmetry mirror plane for a single axis (X, Y, or Z).
This is a global symmetry toggle — it does NOT apply $MakeSymm or
iterate over objects. Use "Apply Symm" for geometry symmetrization.

Uses ported.utils/symmetry_utils.py for low-level symmetry operations.
"""
from __future__ import annotations

from ported.utils.symmetry_utils import toggle_mirror_axis
from ported.utils.coat_ui_utils import show_error


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(axis: str = "X") -> int:
    """
    Toggle mirror symmetry for a single axis.

    Args:
        axis: Which axis to toggle ("X", "Y", or "Z")

    Returns:
        1 if toggle was successful, 0 if axis was invalid
    """
    axis_upper: str = axis.upper()
    if axis_upper not in ("X", "Y", "Z"):
        show_error(f"Invalid mirror axis: {axis} (must be X, Y, or Z)", 3000)
        return 0

    toggle_mirror_axis(axis_upper)
    return 1
