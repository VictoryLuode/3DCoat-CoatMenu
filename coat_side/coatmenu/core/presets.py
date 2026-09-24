"""
CoatMenu - the lists we ship on a first run.

The shipped set is one person's working set - ``QuickTool``, ``Add`` and ``Shade``
(a pie) - in that order, and it is everything we ship: there is no second, optional
set of lists to browse. What each of them holds is decided **at the moment the list
is built**, against the build of 3DCoat that is running, so a list can never hold a
row that does nothing:

* ``QuickTool`` / ``Shade`` - curated lists of 3DCoat's own commands (see the data
  below).

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
from coatmenu.core.config import Menu, MenuConfig, item_from_json, preset_family
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
    "QuickTool": "quicktool/1",
    "Add": "prims/2",
    "Shade": "shade/1",
}

# The lists a fresh install gets, in the order 3DCoat's Scripts menu shows them.
# This is one person's working set - the three lists the author actually uses. Ship
# what is used, nothing else: a fresh install is not a demo of everything the
# extension can build.
DEFAULT_LISTS: tuple[str, ...] = (
    "QuickTool",
    "Add",
    "Shade",
)

# What the editor's "+ New" can build: the lists a fresh install gets, and nothing
# else. They are listed so a list you deleted can be put back.
BUILTIN_LISTS: tuple[str, ...] = DEFAULT_LISTS


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
    """Build one curated list: parse the rows, then drop what this build lacks.

    When an id table we *could* read leaves nothing behind, the list says so instead
    of coming back empty: a menu that opens with no rows at all looks broken, and
    this is the one case where that is our doing rather than the user's.  (With no id
    table to check against, ``_drop_unknown`` keeps the rows - see there.)
    """
    items = [item for item in (item_from_json(raw) for raw in rows) if item is not None]
    universe = _universe()
    kept = _drop_unknown(items, universe)
    if not kept and universe:
        kept = [header(f"{name}: none of its commands exist in this build")]
    return Menu(name=name, items=kept, mode=mode, preset=PRESET_MARKERS[name])


# --- QuickTool / Shade -------------------------------------------------------
# Written down in the config's own JSON shape, so a list edited in the panel can be
# pasted straight back in here. Ids are 3DCoat's; labels are ours.
#
# The shade ids are the ones 3DCoat defines: ``VIEW_GLOSS_ONLY``,
# ``VIEW_SPECULAR_COLOR_ONLY`` and ``VIEW_WIREFRAME``. (``VIEW_GLOSSONLY``,
# ``VIEWSPECULARCOLORONLY`` and ``VIEWWIREFRAME`` - no underscores - are not in
# 3DCoat's id table at all, so a row using them does nothing.)
QUICKTOOL_MENU_ROWS: list = [
    # Synced with the menus the extension actually runs (tests/sync_defaults.py). The
    # live copy also holds six rows from another extension (`[extension]Sculpt_Array`
    # and friends) - this build cannot define those ids, and a shipped row must never
    # do nothing, so they stay out.
    {"header": "Object"},
    "Resample",
    {"id": "SmoothObject", "label": "Smooth All"},
    {"separator": True},
    "RegularGizmo::ToCenterMass",
    {"id": "ToUniformSpaceAll", "label": "Make All Uniform"},
    {"name": "Voxel Operator", "items": [
        {"id": "SeparateHidden", "label": "Separate Hidden Volumes"},
        {"id": "Invert_vox_visibility", "label": "Invert Volumes Visibility"},
    ]},
    {"separator": True},
    {"header": "Scena"},
    {"id": "DefineScaleCorrespondence", "label": "Scene Scale Master"},
]

SHADE_MENU_ROWS: list = [
    {"name": "Shade Mode", "expand": "inline", "position": "right", "items": [
        {"id": "$VIEW_SHADED", "label": "Shade"},
        {"id": "$VIEW_RELIEF_ONLY", "label": "Solid"},
        {"id": "$VIEW_NON_SHADED", "label": "Flat Color"},
        {"id": "$VIEW_GLOSS_ONLY", "label": "Roughness"},
        {"id": "$VIEW_SPECULAR_COLOR_ONLY", "label": "Specular Color"},
        {"id": "$VIEW_METALNESS_ONLY", "label": "Metalness"},
    ]},
    # CastShadows sits on the wheel itself in the live menu, not in Shade Mode.
    {"id": "$CastShadows", "label": "CastShadows", "position": "left"},
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


def quicktool_list(mode: str = LIST) -> Menu:
    """The ``QuickTool`` list: the volume/curve commands reached for while sculpting."""
    return _list_from_rows("QuickTool", QUICKTOOL_MENU_ROWS, mode)


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


# --- installing the shipped lists ---------------------------------------------
_BUILDERS = {
    "QuickTool": quicktool_list,
    "Add": primitives_list,
    "Shade": shade_list,
}


def _check_builders() -> None:
    """A name in a shipped set with no builder is a silent no-op - never worth it."""
    missing = [name for name in BUILTIN_LISTS if name not in _BUILDERS]
    if missing:
        raise RuntimeError(f"no builder for shipped list(s): {', '.join(missing)}")


_check_builders()


def default_lists() -> list[Menu]:
    """Every shipped list, built for this build of 3DCoat (first-run config)."""
    return [_BUILDERS[name]() for name in DEFAULT_LISTS]


def build(name: str) -> Menu | None:
    """One shipped list, built for this build of 3DCoat.

    ``None`` when the name is not one of ours. Used by the editor to put a list
    back after he deleted it (rows built against the 3DCoat that is running now).
    """
    make = _BUILDERS.get(str(name or "").strip())
    return make() if make is not None else None


def _preset_family(marker: str) -> str:
    """``prims/2`` -> ``prims``: which preset a marker belongs to, version aside."""
    return preset_family(marker)


def _was_deleted(config: MenuConfig, fresh: Menu) -> bool:
    """Whether he deleted this shipped list on purpose.

    Two keys, because a list he built himself carries no marker: the preset family
    when there is one, otherwise the name (``MenuConfig.remove_menu`` records
    whichever it has).
    """
    return (preset_family(fresh.preset) in config.removed_presets
            or preset_family(fresh.name) in config.removed_presets)


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
        if _was_deleted(config, fresh):
            # He deleted this one on purpose - the editor records that now. "Not
            # found" is otherwise indistinguishable from "he never had it", and
            # adding it back means his deletion gets undone by an update.
            continue
        if config.find(name) is not None:
            # His list of that name - ours was renamed, or he built his own.
            continue
        if _by_marker(config, fresh.preset) is not None:
            # Ours from an earlier version, under a name of his choosing.
            continue
        config.menus.append(fresh)
        added.append(name)
    return added
