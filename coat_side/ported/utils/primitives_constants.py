"""
Primitives Constants - Magic UI strings for adding primitives to the sculpt scene.

Two separate primitive systems exist in 3DCoat:

1. MESH PRIMITIVES (SculptModels)
   Pre-exported triangle meshes loaded via the Merge tool.
   Workflow:
       coat.ui.cmd(CMD_OPEN_MERGE_TOOL)
       coat.ui.cmd(CMD_MESH_<Name>)

2. BUILT-IN (PARAMETRIC) PRIMITIVES
   3DCoat's internal procedural primitive tool.
   Workflow:
       coat.ui.cmd(CMD_OPEN_PRIMITIVE_TOOL)
       coat.ui.cmd(CMD_PRIM_<Name>)

3. FFD (Free-Form Deformation) PRIMITIVES
   Parametric primitives with attached FFD cage.
   Workflow:
       coat.ui.cmd(CMD_OPEN_PRIMITIVE_TOOL)
       coat.ui.cmd(CMD_FFD_<Name>)

DISCOVERY:
    Magic strings were observed via RMB+MMB on UI elements.
    To discover new ones: RMB+MMB on any UI element → ID is copied to clipboard.
"""


# =============================================================================
# LAUNCH COMMANDS
# =============================================================================

CMD_OPEN_MERGE_TOOL: str = "$SCULP_MERGE"
"""Open the Sculpt Merge tool (prerequisite for mesh primitives)."""

CMD_OPEN_PRIMITIVE_TOOL: str = "$SCULP_PRIM"
"""Open the built-in / FFD primitives tool."""


# =============================================================================
# SCULPT TOOL ACTIVATION COMMANDS
# Used to switch to a specific tool by its magic string ID.
# Discover new ones via RMB+MMB on any tool button in 3DCoat.
# =============================================================================

CMD_TOOL_TRANSFORM: str = "$SCULPT_TRANSFORM"
"""Activate the Transform tool — used as a neutral 'deactivate current tool' step.
Verified: switching to this before re-opening $SCULP_PRIM ensures the primitive
selection cmd is accepted even if the prim tool was already active."""


# =============================================================================
# MESH PRIMITIVES  (via $SCULP_MERGE → $select_<path>)
# Path is relative to 3DCoat documents folder.
# =============================================================================

_MODELS_DIR: str = "UserPrefs/Models/SculptModels"

CMD_MESH_CUBE: str = f"$select_{_MODELS_DIR}/Cube.obj"
CMD_MESH_SPHERE: str = f"$select_{_MODELS_DIR}/Sphere.obj"
CMD_MESH_CYLINDER: str = f"$select_{_MODELS_DIR}/Cylinder.obj"
CMD_MESH_CAPSULE: str = f"$select_{_MODELS_DIR}/Capsule.obj"
CMD_MESH_CONE: str = f"$select_{_MODELS_DIR}/Cone.obj"


# =============================================================================
# BUILT-IN PARAMETRIC PRIMITIVES  (via $MultiObject → $VoxelSculptTool::prm_*)
# =============================================================================

CMD_PRIM_SPHERE: str = "$VoxelSculptTool::prm_SpherePrim"
CMD_PRIM_CUBE: str = "$VoxelSculptTool::prm_CubPrim"
CMD_PRIM_ELLIPSE: str = "$VoxelSculptTool::prm_EllipsePrim"
CMD_PRIM_CYLINDER: str = "$VoxelSculptTool::prm_CylinderPrim"
CMD_PRIM_CONE: str = "$VoxelSculptTool::prm_ConePrim"
CMD_PRIM_TUBE: str = "$VoxelSculptTool::prm_TubePrim"
CMD_PRIM_CAPSULE: str = "$VoxelSculptTool::prm_CapsulePrim"
CMD_PRIM_NGON: str = "$VoxelSculptTool::prm_NGonPrim"
CMD_PRIM_TORUS: str = "$VoxelSculptTool::prm_TorusPrim"
CMD_PRIM_LATHE: str = "$VoxelSculptTool::prm_LathePrim"
"""Revolved / lathed surface primitive."""
CMD_PRIM_TEXT: str = "$VoxelSculptTool::prm_TextPrim"
"""Text mesh primitive."""
CMD_PRIM_IMAGE: str = "$VoxelSculptTool::prm_ImagePrim"
"""Image-based alpha primitive."""


# =============================================================================
# FFD (FREE-FORM DEFORMATION) PRIMITIVES  (via $MultiObject → $VoxelSculptTool::ff*)
# =============================================================================

CMD_FFD_BLOB: str = "$VoxelSculptTool::ffBlob"
"""Sphere with an attached FFD cage."""
CMD_FFD_CUBE: str = "$VoxelSculptTool::ffCube"
"""Cube with an attached FFD cage."""
CMD_FFD_CYLINDER: str = "$VoxelSculptTool::ffCylinder"
"""Cylinder with an attached FFD cage."""
CMD_FFD_TORUS: str = "$VoxelSculptTool::ffTorus"
"""Torus with an attached FFD cage."""
CMD_FFD_RING: str = "$VoxelSculptTool::ffRing"
"""Cylinder with a hole (ring) — with FFD cage."""
CMD_FFD_DISC: str = "$VoxelSculptTool::ffDisc"
"""Flat ring / disc — with FFD cage."""
CMD_FFD_PATCH: str = "$VoxelSculptTool::ffPatch"
"""Planar square patch — with FFD cage."""
CMD_FFD_ROUND: str = "$VoxelSculptTool::ffRound"
"""Rounded primitive — with FFD cage."""


# =============================================================================
# LABEL MAPS (useful for UI display)
# =============================================================================

MESH_PRIMITIVES: dict[str, str] = {
    "Cube":     CMD_MESH_CUBE,
    "Sphere":   CMD_MESH_SPHERE,
    "Cylinder": CMD_MESH_CYLINDER,
    "Capsule":  CMD_MESH_CAPSULE,
    "Cone":     CMD_MESH_CONE,
}

BUILTIN_PRIMITIVES: dict[str, str] = {
    "Sphere":   CMD_PRIM_SPHERE,
    "Cube":     CMD_PRIM_CUBE,
    "Ellipse":  CMD_PRIM_ELLIPSE,
    "Cylinder": CMD_PRIM_CYLINDER,
    "Cone":     CMD_PRIM_CONE,
    "Tube":     CMD_PRIM_TUBE,
    "Capsule":  CMD_PRIM_CAPSULE,
    "NGon":     CMD_PRIM_NGON,
    "Torus":    CMD_PRIM_TORUS,
    "Lathe":    CMD_PRIM_LATHE,
    "Text":     CMD_PRIM_TEXT,
    "Image":    CMD_PRIM_IMAGE,
}

FFD_PRIMITIVES: dict[str, str] = {
    "Blob":     CMD_FFD_BLOB,
    "Cube":     CMD_FFD_CUBE,
    "Cylinder": CMD_FFD_CYLINDER,
    "Torus":    CMD_FFD_TORUS,
    "Ring":     CMD_FFD_RING,
    "Disc":     CMD_FFD_DISC,
    "Patch":    CMD_FFD_PATCH,
    "Round":    CMD_FFD_ROUND,
}
