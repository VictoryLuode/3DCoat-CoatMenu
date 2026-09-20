"""
Scene_AddPrimitive Operator

Add a primitive object to the sculpt scene.

Supports three primitive systems:

  PrimitiveKind.MESH     — SculptModel .obj files loaded via the Merge tool.
                           Prerequisite: CMD_OPEN_MERGE_TOOL ($SCULP_MERGE).

  PrimitiveKind.BUILTIN  — 3DCoat's parametric primitive tool.
                           Prerequisite: CMD_OPEN_PRIMITIVE_TOOL ($SCULP_PRIM).

  PrimitiveKind.FFD      — Parametric primitive + FFD cage.
                           Prerequisite: CMD_OPEN_PRIMITIVE_TOOL ($SCULP_PRIM).

Usage:
    from ported.ops.Scene_AddPrimitive import main as op_add_prim, PrimitiveKind
    from ported.utils.primitives_constants import CMD_MESH_CUBE

    op_add_prim(kind=PrimitiveKind.MESH, cmd=CMD_MESH_CUBE)
"""
import coat
from enum import Enum
from ported.utils.primitives_constants import (
    CMD_OPEN_MERGE_TOOL,
    CMD_OPEN_PRIMITIVE_TOOL,
    CMD_TOOL_TRANSFORM,
)
from ported.utils.coat_ui_utils import wait_frames, show_message, show_error

# Re-export for callers who only import from here
from ported.utils.primitives_constants import (  # noqa: F401
    CMD_MESH_CUBE, CMD_MESH_SPHERE, CMD_MESH_CYLINDER,
    CMD_MESH_CAPSULE, CMD_MESH_CONE,
    CMD_PRIM_SPHERE, CMD_PRIM_CUBE, CMD_PRIM_ELLIPSE,
    CMD_PRIM_CYLINDER, CMD_PRIM_CONE, CMD_PRIM_TUBE,
    CMD_PRIM_CAPSULE, CMD_PRIM_NGON, CMD_PRIM_TORUS,
    CMD_PRIM_LATHE, CMD_PRIM_TEXT, CMD_PRIM_IMAGE,
    CMD_FFD_BLOB, CMD_FFD_CUBE, CMD_FFD_CYLINDER,
    CMD_FFD_TORUS, CMD_FFD_RING, CMD_FFD_DISC,
    CMD_FFD_PATCH, CMD_FFD_ROUND,
)


# =============================================================================
# PRIMITIVE KIND ENUM
# =============================================================================

class PrimitiveKind(Enum):
    """Which primitive system to invoke."""
    MESH = "mesh"
    """SculptModel .obj mesh via the Merge tool."""
    BUILTIN = "builtin"
    """Parametric built-in primitive."""
    FFD = "ffd"
    """Parametric FFD (free-form deformation) primitive."""


# Map each kind to the 3DCoat UI command that opens the correct tool
_KIND_LAUNCH_CMD: dict[PrimitiveKind, str] = {
    PrimitiveKind.MESH: CMD_OPEN_MERGE_TOOL,
    PrimitiveKind.BUILTIN: CMD_OPEN_PRIMITIVE_TOOL,
    PrimitiveKind.FFD: CMD_OPEN_PRIMITIVE_TOOL,
}


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    kind: PrimitiveKind,
    cmd: str,
    label: str = "",
) -> bool:
    """
    Add a primitive to the sculpt scene.

    Args:
        kind:  Which primitive system (MESH / BUILTIN / FFD)
        cmd:   The magic UI string for the specific primitive
               (from ported.utils.primitives_constants)
        label: Human-readable name for confirmation message (optional)

    Returns:
        True if the command was issued, False on error
    """
    if not cmd:
        show_error("No primitive command provided", 2000)
        return False

    # Switch to a neutral tool first so that if $SCULP_PRIM / $SCULP_MERGE is
    # already active the re-open resets properly and the primitive selection cmd
    # is accepted.  Without this, firing $SCULP_PRIM when the prim tool is
    # already open leaves it in a state where the second cmd returns False.
    # No tool-detection API exists in coat, so we always switch out first.
    coat.ui.cmd(CMD_TOOL_TRANSFORM)
    launch_cmd: str = _KIND_LAUNCH_CMD[kind]
    coat.ui.cmd(launch_cmd)
    coat.ui.cmd(cmd)

    name: str = label or cmd.split(
        "::")[-1].replace("prm_", "").replace("ff", "FFD ")
    show_message(f"Adding primitive {name}", 2000)
    return True


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def add_mesh_primitive(cmd: str, label: str = "") -> bool:
    """Add a SculptModel mesh primitive."""
    return main(PrimitiveKind.MESH, cmd, label)


def add_builtin_primitive(cmd: str, label: str = "") -> bool:
    """Add a built-in parametric primitive."""
    return main(PrimitiveKind.BUILTIN, cmd, label)


def add_ffd_primitive(cmd: str, label: str = "") -> bool:
    """Add an FFD primitive."""
    return main(PrimitiveKind.FFD, cmd, label)
