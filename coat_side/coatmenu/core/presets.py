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

from coatmenu.core import catalog
from coatmenu.core.config import MenuConfig, MenuList
from coatmenu.core.menu_model import (
    COMMAND,
    LIST,
    PRESET,
    MenuItem,
    header,
    separator,
    sequence,
    submenu,
)

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
PRESET_MARKERS = {"Prims": "prims/2", "Tools": "tools/1", "Presets": "presets/1",
                  "LKS": "lks/1"}


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


def tool_rows() -> list[tuple[str, list[MenuItem]]]:
    """(panel section, rows) exactly as 3DCoat groups its own tool panel."""
    groups: dict[str, list[MenuItem]] = {}
    for entry in catalog.read_my_tools():
        # Tools 3DCoat's own panel definitions do not put in a section (CAD/model
        # tools mostly) still need a heading.
        groups.setdefault(entry.hint or "General", []).append(
            MenuItem(label=entry.label, kind=COMMAND, cid=entry.cmd_string))
    return list(groups.items())


def tools_list(mode: str = LIST) -> MenuList:
    """The ``Tools`` list: your tool presets, grouped like 3DCoat's own panel.

    A hundred tools flat in one menu would be unusable, so each of 3DCoat's panel
    sections becomes a submenu - the section names are 3DCoat's own.
    """
    items: list[MenuItem] = []
    for name, rows in tool_rows():
        items.append(submenu(f"{name}  ({len(rows)})", rows))
    if not items:
        items.append(header("no CustomTools presets found"))
    return MenuList(name="Tools", items=items, mode=mode,
                    preset=PRESET_MARKERS["Tools"])


def preset_rows() -> list[MenuItem]:
    """The user's tool presets, in the order 3DCoat's Presets panel shows them."""
    return [MenuItem(label=e.label, kind=PRESET, cid=e.cid)
            for e in catalog.read_presets()]


def presets_list(mode: str = LIST) -> MenuList:
    """The ``Presets`` list: the presets stored in 3DCoat's Presets panel.

    Unlike ``Tools`` (which only switches the tool), a preset carries the tool
    *and* the settings saved with it, and is applied through
    ``AppOptions.ActivateToolPreset`` - so a row restores exactly what you stored.
    """
    rows = preset_rows()
    items = rows or [header("no presets in UserPrefs/Presets")]
    return MenuList(name="Presets", items=items, mode=mode,
                    preset=PRESET_MARKERS["Presets"])


def lks_list(mode: str = LIST) -> MenuList:
    """The ``LKS`` list: the radial menus from the LKS extension.

    LKS owns those JSON files and its users edit them in place, so this is a
    read-only import - one submenu per LKS menu, with LKS's own labels and order.
    """
    from coatmenu.core import lks

    items: list[MenuItem] = []
    for menu in lks.read_menus():
        items.append(submenu(f"{menu.name}  ({len(menu.items)})", menu.items))
    if not items:
        items.append(header("no LKS radial menus found"))
    return MenuList(name="LKS", items=items, mode=mode,
                    preset=PRESET_MARKERS["LKS"])


def install_presets(config: MenuConfig,
                    names: tuple[str, ...] = ("Prims", "Tools", "Presets", "LKS")) -> list[str]:
    """Add missing preset lists, and refresh ones shipped by an older version.

    A preset list is recognised by its ``preset`` marker: a list you built by
    hand - even one called ``Prims`` - has no marker and is never touched.
    """
    built = {"Prims": primitives_list, "Tools": tools_list, "Presets": presets_list,
             "LKS": lks_list}
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
