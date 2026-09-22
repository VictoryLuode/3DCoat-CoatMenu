"""
CoatMenu - the lists we ship on a first run.

The shipped set is one person's own set - ``Sculpt``, ``Modeling``, ``Add``,
``Tools``, ``Common``, ``Shade`` and ``Sculpt Ops`` - in that order. What each of
them holds is decided **at the moment the list is built**, against the build of
3DCoat that is running, so a list can never hold a row that does nothing:

* ``Common`` - the everyday commands, grouped the way 3DCoat's main menu groups
  them (read from ``cTemplates``).
* ``Tools`` - the tool presets in your ``CustomTools``, grouped by the section
  3DCoat's own panel puts them in.
* ``Sculpt Ops`` - 3DCoat's own object commands (the ones on the VoxTree
  right-click menu), sorted into groups we chose.
* ``Sculpt`` / ``Modeling`` / ``Shade`` - curated lists of 3DCoat's own commands
  (see the data below).

``Add`` is the one list whose rows fire a *sequence* of commands:

    $SCULPT_TRANSFORM                      neutralise whatever tool is active
    $SCULP_PRIM                            open the primitive tool
    $VoxelSculptTool::prm_*  /  ::ff*      pick the shape

Those ids and that order are 3DCoat's own (its ``Scripts/Missions/Primitives.as``
drives the same buttons). Reaching primitives from a menu is an idea earlier
3DCoat extensions had - this is our own take on it, built from 3DCoat's ids.

Every id that is written down here is looked up in
:func:`coatmenu.core.catalog.known_command_ids` - 3DCoat's own id table - before
it becomes a row, and left out when this build does not define it. That is what
keeps a curated list honest on a build whose commands differ from the one it was
written on.
"""
from __future__ import annotations

from coatmenu.core import catalog
from coatmenu.core.config import Menu, MenuConfig, item_from_json
from coatmenu.core.menu_model import (
    COMMAND,
    LIST,
    PIE,
    SUBMENU,
    MenuItem,
    header,
    separator,
    sequence,
    submenu,
)

# --- command ids (3DCoat's own, as its UI uses them) --------------------------
NEUTRALISE = "$SCULPT_TRANSFORM"
PRIM_TOOL = "$SCULP_PRIM"

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
# so the installer offers the new rows (a hand-built list of the same name has no
# marker and is never touched; a shipped list the user has edited only ever gains
# whole lists - see install_presets). The family (the part before the "/") is what
# identifies a list we shipped once, under whatever name the user gave it.
PRESET_MARKERS = {
    "Sculpt": "sculpt/1",
    "Modeling": "modeling/1",
    "Add": "prims/2",
    "Tools": "tools/1",
    "Common": "common/1",
    "Shade": "shade/1",
    "Sculpt Ops": "sculptops/1",
}

# The lists a fresh install gets, in the order 3DCoat's Scripts menu shows them.
DEFAULT_LISTS: tuple[str, ...] = (
    "Sculpt",
    "Modeling",
    "Add",
    "Tools",
    "Common",
    "Shade",
    "Sculpt Ops",
)


def _universe() -> set[str]:
    """The command ids this build of 3DCoat defines (empty when unknowable)."""
    return catalog.known_command_ids()


def _known(universe: set[str], cid: str) -> bool:
    """True when *cid* is a command this build has (or when we cannot tell)."""
    if not universe:
        return True
    key = str(cid or "").lstrip("$").strip().lower()
    if not key:
        return False
    return key in universe or key.split("::")[0] in universe


def _drop_unknown(items: list[MenuItem], universe: set[str]) -> list[MenuItem]:
    """Rows whose command this build does not define are left out; rest is kept.

    An empty *universe* means the program folder could not be read, so nothing can
    be checked: the rows stay as they are rather than being dropped wholesale.
    """
    out: list[MenuItem] = []
    for item in items:
        if item.kind == SUBMENU:
            children = _drop_unknown(list(item.children or []), universe)
            if children:
                item.children = children
                out.append(item)
            continue
        if item.kind == COMMAND and item.cid and not _known(universe, item.cid):
            continue
        out.append(item)
    return out


def _list_from_rows(name: str, rows: list, mode: str = LIST) -> Menu:
    """Build one curated list: parse the rows, then drop what this build lacks."""
    items = [item for item in (item_from_json(raw) for raw in rows) if item is not None]
    return Menu(name=name, items=_drop_unknown(items, _universe()), mode=mode,
                preset=PRESET_MARKERS[name])


# --- Sculpt / Modeling / Shade ------------------------------------------------
# Written down in the config's own JSON shape, so a list edited in the panel can be
# pasted straight back in here. Ids are 3DCoat's; labels are ours.
#
# The shade ids are the ones 3DCoat defines: ``VIEW_GLOSS_ONLY``,
# ``VIEW_SPECULAR_COLOR_ONLY`` and ``VIEW_WIREFRAME``. (``VIEW_GLOSSONLY``,
# ``VIEWSPECULARCOLORONLY`` and ``VIEWWIREFRAME`` - no underscores - are not in
# 3DCoat's id table at all, so a row using them does nothing.)
SCULPT_MENU_ROWS: list = [
    {"header": "Object"},
    {"id": "BendVolume", "label": "Array/Bend Volume"},
    {"id": "TubeOrModels", "label": "Attach Tube or Models Array"},
    "Resample",
    "RegularGizmo::ToCenterMass",
    {"id": "ToUniformSpaceAll", "label": "Make All Uniform"},
    {"name": "Voxel Operator", "items": [
        {"id": "SeparateHidden", "label": "Separate Hidden Volumes"},
        {"id": "Invert_vox_visibility", "label": "Invert Volumes Visibility"},
        {"id": "SCULP_HIDE", "label": "Vox Hide"},
    ]},
    {"separator": True},
    {"header": "Scena"},
    {"id": "DefineScaleCorrespondence", "label": "Scene Scale Master"},
]

MODELING_MENU_ROWS: list = [
    "ApplyTopoSubdiv",
    "Bevel",
    {"id": "RtWeldingVertexs", "label": "WeldingVertexs"},
    {"id": "SculptMesh", "label": "Display In Sculpt"},
    "Subdivide1",
    "Subdivide2",
]

SHADE_MENU_ROWS: list = [
    {"name": "Shade Mode", "expand": "inline", "position": "right", "items": [
        {"id": "$CastShadows", "label": "CastShadows"},
        {"id": "$VIEW_SHADED", "label": "Shade"},
        {"id": "$VIEW_RELIEF_ONLY", "label": "Solid"},
        {"id": "$VIEW_NON_SHADED", "label": "Flat Color"},
        {"id": "$VIEW_GLOSS_ONLY", "label": "Roughness"},
        {"id": "$VIEW_SPECULAR_COLOR_ONLY", "label": "Specular Color"},
        {"id": "$VIEW_METALNESS_ONLY", "label": "Metalness"},
    ]},
    {"name": "Shade Setting", "expand": "inline", "position": "top-left", "items": [
        {"id": "$BackfaceCulling", "label": "BackfaceCulling"},
        {"id": "$GreyscaleLight", "label": "HDR Grey Mode"},
    ]},
    {"name": "Overlay", "expand": "inline", "position": "bottom-left", "items": [
        {"id": "$SHOW_AXIS", "label": "Axis"},
        {"id": "$VIEW_WIREFRAME", "label": "WireFrame"},
        {"id": "$RenderSculptSelection", "label": "Selection"},
    ]},
]


def sculpt_list(mode: str = LIST) -> Menu:
    """The ``Sculpt`` list: the volume/curve commands reached for while sculpting."""
    return _list_from_rows("Sculpt", SCULPT_MENU_ROWS, mode)


def modeling_list(mode: str = LIST) -> Menu:
    """The ``Modeling`` list: subdivision and retopo-side commands."""
    return _list_from_rows("Modeling", MODELING_MENU_ROWS, mode)


def shade_list(mode: str = PIE) -> Menu:
    """The ``Shade`` pie: view modes, shading switches and overlays."""
    return _list_from_rows("Shade", SHADE_MENU_ROWS, mode)


# --- primitives --------------------------------------------------------------
def _prim_rows(pairs: list[tuple[str, str]], universe: set[str]) -> list[MenuItem]:
    return [sequence(label, [NEUTRALISE, PRIM_TOOL, f"$VoxelSculptTool::{param}"])
            for label, param in pairs if _known(universe, param)]


def primitive_groups() -> list[tuple[str, list[MenuItem]]]:
    """(group label, rows) - the shapes, in the order the menu presents them.

    A ``Mesh Prims`` group used to sit in here, pointing
    ``$select_UserPrefs/Models/SculptModels/<shape>.obj`` at files 3DCoat does not
    ship - the shapes live in the program folder's ``data/ObjPens`` - so every row
    of it did nothing. It is gone rather than shipped broken.
    """
    universe = _universe()
    return [
        ("Built-in Prims\u2026", _prim_rows(BUILTIN_PRIMITIVES, universe)),
        ("FFD Prims\u2026", _prim_rows(FFD_PRIMITIVES, universe)),
    ]


def primitives_list(mode: str = LIST) -> Menu:
    """The ``Add`` list.

    The built-in shapes sit straight on the list - they are the ones you reach for
    constantly - while the FFD group stays folded into a submenu so the list does
    not grow past a screenful.
    """
    items: list[MenuItem] = [builtin_row(label, param)
                             for label, param in BUILTIN_PRIMITIVES
                             if _known(_universe(), param)]
    items.append(separator())
    for label, rows in primitive_groups()[1:]:
        if rows:
            items.append(submenu(label, rows))
    return Menu(name="Add", items=items, mode=mode,
                preset=PRESET_MARKERS["Add"])


def builtin_row(label: str, param: str) -> MenuItem:
    """One built-in primitive: neutralise, open the tool, pick the shape."""
    return sequence(label, [NEUTRALISE, PRIM_TOOL, f"$VoxelSculptTool::{param}"])


# --- Sculpt Ops: 3DCoat's own object commands, in groups we chose -------------
# Ids only. Every one of them is looked up in 3DCoat's own id table when the list
# is built (see `sculpt_ops_groups`), and one this build does not define is
# skipped - so the list can never contain a row that does nothing. Groups that
# come back empty are dropped as well.
SCULPT_OPS: list[tuple[str, list[str]]] = [
    ("Decimate", [
        "Decimate",
        "Decimate2X",
        "Decimate4X",
        "Decimate8X",
        "Decimate16X",
        "Reduce2X",
        "Reduce4X",
        "Reduce8X",
    ]),
    ("Density & Resample", [
        "IncDencity2X",
        "DecDencity2X",
        "Resample",
        "RESAMPLE4SCREEN_TOOL",
        "ToUniformSpace",
        "ToGlobalSpace",
        "ToUniformSpaceAll",
        "ShowDensityNearVolumes",
    ]),
    ("Boolean", [
        "LiveUnion",
        "LiveSubtraction",
        "LiveIntersection",
        "NormalSculptLayer",
        "CollapseBoolTree",
        "BooleanRules",
        "SoftBooleansForVolumes",
        "SubtractFrom",
        "IntersectWith",
        "CopySubtractFrom",
        "RemoveIntersectionWith",
    ]),
    ("Merge & Clone", [
        "MergeVisible",
        "MergeSubtree",
        "MergeSelected",
        "MergeTo",
        "MoveTo",
        "PlainMergeVisible",
        "PlainMergeSubtree",
        "PlainMergeSelected",
        "CloneVoxTree",
        "CloneInstance",
        "CloneSymm",
        "InstanceToParentInstances",
    ]),
    ("Hide, Show & Ghost", [
        "Toggle_ghosting",
        "Isolate_ghosting",
        "Toggle_vox_visibility",
        "Invert_vox_visibility",
        "HideButCurrent",
        "UnhideAll",
        "ShowAll",
        "ShowSubtree",
        "InvertHide",
        "DeleteHidden",
        "SeparateHidden",
    ]),
    ("Object Tools", [
        "SmoothObject",
        "CleanSurface",
        "CloseHoles",
        "CloseSurfaceHoles",
        "Decompose",
        "DecomposeFrozen",
        "Shell",
        "MakeVoxHull",
        "CreateSurfaceShell",
        "FlipNormals",
        "ExtrudeVO",
        "AddVoxTree",
    ]),
    ("Autopo & Retopo", [
        "Quadrangulate",
        "QuadrangulateAndMerge",
        "QuadrangulateAndMergeDP",
        "QuadrangulateAndMergePtex",
        "OldStyleQuads",
        "GetObjectFromRetopoRoom",
        "DecimateToRetopo",
        "DecimateAllToRetopo",
        "CustomRetopers",
    ]),
]


def sculpt_ops_groups() -> list[tuple[str, list[MenuItem]]]:
    """(group label, rows) for the object commands 3DCoat itself defines.

    The labels come from 3DCoat's own definitions, never from us, and an id that
    is not there is left out: a curated list plus a lookup is what keeps this list
    honest on a build whose commands differ from the one it was written on.
    """
    universe = _universe()
    known = {entry.cid.lstrip("$").lower(): entry
             for entry in catalog.read_menu_commands()}
    groups: list[tuple[str, list[MenuItem]]] = []
    for label, ids in SCULPT_OPS:
        rows: list[MenuItem] = []
        for cid in ids:
            entry = known.get(cid.lstrip("$").lower())
            if entry is None and not _known(universe, cid):
                continue
            rows.append(MenuItem(label=(entry.label if entry and entry.label else cid),
                                 kind=COMMAND,
                                 cid=(entry.cmd_string if entry is not None
                                      else "$" + cid.lstrip("$"))))
        if rows:
            groups.append((label, rows))
    return groups


def sculpt_ops_list(mode: str = LIST) -> Menu:
    """The ``Sculpt Ops`` list: 3DCoat's own object commands, one submenu per group.

    These are the entries 3DCoat puts on the VoxTree right-click menu - decimate,
    resample, the live booleans, merge, ghosting - grouped so a pie can reach them
    without a trip to the VoxTree.
    """
    items: list[MenuItem] = []
    for name, rows in sculpt_ops_groups():
        items.append(submenu(f"{name}  ({len(rows)})", rows))
    if not items:
        items.append(header("3DCoat's own object commands were not found"))
    return Menu(name="Sculpt Ops", items=items, mode=mode,
                preset=PRESET_MARKERS["Sculpt Ops"])


# --- Tools -------------------------------------------------------------------
def tool_rows() -> list[tuple[str, list[MenuItem]]]:
    """(panel section, rows) exactly as 3DCoat groups its own tool panel."""
    groups: dict[str, list[MenuItem]] = {}
    for entry in catalog.read_my_tools():
        # Tools 3DCoat's own panel definitions do not put in a section (CAD/model
        # tools mostly) still need a heading.
        groups.setdefault(entry.hint or "General", []).append(
            MenuItem(label=entry.label, kind=COMMAND, cid=entry.cmd_string))
    return list(groups.items())


def tools_list(mode: str = LIST) -> Menu:
    """The ``Tools`` list: your tool presets, grouped like 3DCoat's own panel.

    A hundred tools flat in one menu would be unusable, so each of 3DCoat's panel
    sections becomes a submenu - the section names are 3DCoat's own.
    """
    items: list[MenuItem] = []
    for name, rows in tool_rows():
        items.append(submenu(f"{name}  ({len(rows)})", rows))
    if not items:
        items.append(header("no CustomTools presets found"))
    return Menu(name="Tools", items=items, mode=mode,
                preset=PRESET_MARKERS["Tools"])


# --- Common ------------------------------------------------------------------
# The main menus whose commands get reached for constantly. Using 3DCoat's own
# grouping keeps "common" 3DCoat's opinion rather than ours.
COMMON_MENUS = ("Edit", "View", "Freeze", "Symmetry", "Hide", "Layers")


def common_groups(menus: tuple[str, ...] = COMMON_MENUS) -> list[tuple[str, list[MenuItem]]]:
    """(menu name, rows) for the everyday commands, in 3DCoat's own order."""
    wanted = {name.lower() for name in menus}
    found: dict[str, list[MenuItem]] = {}
    for entry in catalog.read_all_commands():
        hint = entry.hint or ""
        if not hint.startswith("MainMenu/"):
            continue
        name = hint.split("/", 1)[1]
        if name.lower() not in wanted:
            continue
        found.setdefault(name, []).append(
            MenuItem(label=entry.label, kind=COMMAND, cid=entry.cmd_string))
    return [(name, found[name]) for name in menus if name in found]


def common_list(mode: str = LIST) -> Menu:
    """The ``Common`` list: everyday commands, grouped as 3DCoat groups its menus.

    Undo/Redo and the transform commands live here, along with view shading,
    freeze, symmetry and hide - the things reached for between sculpt strokes.
    """
    items: list[MenuItem] = []
    for name, rows in common_groups():
        items.append(submenu(f"{name}  ({len(rows)})", rows))
    if not items:
        items.append(header("no main-menu commands found"))
    return Menu(name="Common", items=items, mode=mode,
                preset=PRESET_MARKERS["Common"])


# --- installing the shipped lists ---------------------------------------------
_BUILDERS = {
    "Sculpt": sculpt_list,
    "Modeling": modeling_list,
    "Add": primitives_list,
    "Tools": tools_list,
    "Common": common_list,
    "Shade": shade_list,
    "Sculpt Ops": sculpt_ops_list,
}


def default_lists() -> list[Menu]:
    """Every shipped list, built for this build of 3DCoat (first-run config)."""
    return [_BUILDERS[name]() for name in DEFAULT_LISTS]


def _preset_family(marker: str) -> str:
    """``prims/2`` -> ``prims``: which preset a marker belongs to, version aside."""
    return str(marker or "").split("/")[0].strip().lower()


def _by_marker(config: MenuConfig, marker: str):
    """A menu we shipped once, found by its marker rather than its name.

    The name is not a reliable key: the user is free to rename a built-in menu, and
    if we only looked for ``Add`` we would add a second one next to his
    ``Add Prims``. Compared per *family* (``prims``), so every version of the same
    preset - and every name he gave it - counts as the same list.
    """
    family = _preset_family(marker)
    if not family:
        return None
    for menu in config.menus:
        if _preset_family(menu.preset) == family:
            return menu
    return None


def install_presets(config: MenuConfig, names: tuple[str, ...] = DEFAULT_LISTS) -> list[str]:
    """Add preset lists that are **missing**. A menu that exists is never touched.

    The rule this exists to hold (see AGENTS.md): the menus in the config are the
    user's, including the ones we shipped with - the moment a list is in his file
    it is his. So this is add-only, and "add" means *a whole list that is not
    there*: no refreshing an older version of ours, no topping up rows of an
    edited one, no renaming, no reordering, no marker rewrite. A list that has
    become stale is the user's to delete or rebuild in the editor.

    A hand-built list of the same name (no ``preset`` marker) always wins, and is
    left alone too.
    """
    added: list[str] = []
    for name in names:
        make = _BUILDERS.get(name)
        if make is None:
            continue
        fresh = make()
        if config.find(name) is not None:
            # His list of that name - ours was renamed, or he built his own.
            continue
        if _by_marker(config, fresh.preset) is not None:
            # Ours from an earlier version, under a name of his choosing.
            continue
        config.menus.append(fresh)
        added.append(name)
    return added
