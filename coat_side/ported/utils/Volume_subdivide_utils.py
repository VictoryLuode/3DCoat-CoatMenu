"""
Volume Subdivide Utilities - Subdivide and symmetry operations on Volumes.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Operators in `_ops/` own Config dataclasses and call these functions.
"""
import coat

from ported.utils.coat_ui_utils import wait_frames

# =============================================================================
# MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

CMD_SUBDIVIDE: str = "$VoxTreeBranch.IncRes_HINT.Root"
CMD_MAKE_SYMMETRICAL: str = "$MakeSymm"

# =============================================================================
# DEFAULTS
# =============================================================================

MESH_OP_WAIT_FRAMES: int = 2


# =============================================================================
# FUNCTIONS (raw args)
# =============================================================================

def subdivide_once() -> None:
    """Subdivide current Volume once (approximately doubles polycount)."""
    coat.ui.cmd(CMD_SUBDIVIDE)
    wait_frames(MESH_OP_WAIT_FRAMES)


def make_symmetrical() -> None:
    """Make the current Volume symmetrical along its symmetry axis."""
    coat.ui.cmd(CMD_MAKE_SYMMETRICAL)
    wait_frames(MESH_OP_WAIT_FRAMES)
