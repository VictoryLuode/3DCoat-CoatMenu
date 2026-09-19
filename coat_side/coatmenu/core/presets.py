"""
CoatMenu - built-in preset lists.

The ``Prims`` list is a port of the LKS extension's "Add Prims" radial menu
(``LKS/data/library/radial_menus/LKS_Radial_AddPrims.json``).  LKS fires three
3DCoat commands in order for every entry, and this port keeps that exact order:

    $SCULPT_TRANSFORM                      neutralise whatever tool is active
    $SCULP_PRIM   /  $SCULP_MERGE          open the primitive / merge tool
    $VoxelSculptTool::prm_*  /  $select_*  pick the shape

Those command strings are 3DCoat's own UI ids (LKS's
``utils/primitives_constants.py``: "magic strings observed via RMB+MMB on UI
elements"), so nothing here is invented - the sequence is the part 3DCoat needs
to make the pick land.
"""
from __future__ import annotations

from coatmenu.core.config import MenuConfig, MenuList
from coatmenu.core.menu_model import LIST, MenuItem, sequence, submenu

# --- command ids (from LKS utils/primitives_constants.py) --------------------
NEUTRALISE = "$SCULPT_TRANSFORM"
PRIM_TOOL = "$SCULP_PRIM"
MERGE_TOOL = "$SCULP_MERGE"
MODELS_DIR = "UserPrefs/Models/SculptModels"

BUILTIN_PRIMITIVES: list[tuple[str, str]] = [
    ("Sphere", "prm_SpherePrim"),
    ("Cube", "prm_CubPrim"),
    ("Ellipse", "prm_EllipsePrim"),
    ("Cylinder", "prm_CylinderPrim"),
    ("Cone", "prm_ConePrim"),
    ("Tube", "prm_TubePrim"),
    ("Capsule", "prm_CapsulePrim"),
    ("NGon", "prm_NGonPrim"),
    ("Torus", "prm_TorusPrim"),
    ("Lathe", "prm_LathePrim"),
    ("Text", "prm_TextPrim"),
    ("Image", "prm_ImagePrim"),
]

MESH_PRIMITIVES: list[tuple[str, str]] = [
    ("Cube", "Cube.obj"),
    ("Sphere", "Sphere.obj"),
    ("Cylinder", "Cylinder.obj"),
    ("Capsule", "Capsule.obj"),
    ("Cone", "Cone.obj"),
]

FFD_PRIMITIVES: list[tuple[str, str]] = [
    ("Blob", "ffBlob"),
    ("Cube", "ffCube"),
    ("Cylinder", "ffCylinder"),
    ("Torus", "ffTorus"),
    ("Ring", "ffRing"),
    ("Disc", "ffDisc"),
    ("Patch", "ffPatch"),
    ("Round", "ffRound"),
]


def builtin_row(label: str, param: str) -> MenuItem:
    return sequence(label, [NEUTRALISE, PRIM_TOOL, f"$VoxelSculptTool::{param}"])


def mesh_row(label: str, filename: str) -> MenuItem:
    return sequence(label, [NEUTRALISE, MERGE_TOOL, f"$select_{MODELS_DIR}/{filename}"])


def ffd_row(label: str, param: str) -> MenuItem:
    return sequence(label, [NEUTRALISE, PRIM_TOOL, f"$VoxelSculptTool::{param}"])


def primitive_groups() -> list[tuple[str, list[MenuItem]]]:
    """(group label, rows) - the three groups LKS groups its pie menu into."""
    return [
        ("Built-in Prims\u2026", [builtin_row(l, p) for l, p in BUILTIN_PRIMITIVES]),
        ("Mesh Prims\u2026", [mesh_row(l, f) for l, f in MESH_PRIMITIVES]),
        ("FFD Prims\u2026", [ffd_row(l, p) for l, p in FFD_PRIMITIVES]),
    ]


def primitives_list(mode: str = LIST) -> MenuList:
    """The ``Prims`` list: one submenu per group, same grouping as LKS."""
    items: list[MenuItem] = [submenu(label, rows) for label, rows in primitive_groups()]
    return MenuList(name="Prims", items=items, mode=mode)


def install_presets(config: MenuConfig, names: tuple[str, ...] = ("Prims",)) -> list[str]:
    """Add any missing preset list; returns the names that were added."""
    built = {"Prims": primitives_list}
    added: list[str] = []
    for name in names:
        if config.find(name) is not None:
            continue
        make = built.get(name)
        if make is None:
            continue
        config.lists.append(make())
        added.append(name)
    return added
