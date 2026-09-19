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
from coatmenu.core.menu_model import LIST, MenuItem, separator, sequence, submenu

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


# Version markers for the lists we ship: bump the number when the preset changes
# so the installer refreshes the user's copy (a hand-built list of the same name
# has no marker and is never touched).
PRESET_MARKERS = {"Prims": "prims/2"}


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
    """The ``Prims`` list.

    The built-in shapes sit straight on the list - they are the ones you reach
    for constantly - while the mesh and FFD groups stay folded into submenus so
    the list does not grow past a screenful.
    """
    items: list[MenuItem] = [builtin_row(label, param)
                             for label, param in BUILTIN_PRIMITIVES]
    items.append(separator())
    for label, rows in primitive_groups()[1:]:
        items.append(submenu(label, rows))
    return MenuList(name="Prims", items=items, mode=mode,
                    preset=PRESET_MARKERS["Prims"])


def install_presets(config: MenuConfig, names: tuple[str, ...] = ("Prims",)) -> list[str]:
    """Add missing preset lists, and refresh ones shipped by an older version.

    A preset list is recognised by its ``preset`` marker: a list you built by
    hand - even one called ``Prims`` - has no marker and is never touched.
    """
    built = {"Prims": primitives_list}
    added: list[str] = []
    for name in names:
        make = built.get(name)
        if make is None:
            continue
        fresh = make()
        existing = config.find(name)
        if existing is None:
            config.lists.append(fresh)
            added.append(name)
        elif existing.preset and existing.preset != fresh.preset:
            config.lists[config.lists.index(existing)] = fresh
            added.append(f"{name} (refreshed)")
    return added
