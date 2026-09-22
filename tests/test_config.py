"""
Config model + launcher generation tests - no Qt, no 3DCoat.

Run:  python tests/test_config.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
sys.path.insert(0, HERE)
sys.path.insert(0, COAT_SIDE)

from fake_coat import install_fake_coat  # noqa: E402

DOCS = tempfile.mkdtemp(prefix="coatmenu-config-")
MENU_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "CustomMenu", "VoxelsCustom")
os.makedirs(MENU_DIR, exist_ok=True)
with open(os.path.join(MENU_DIR, "$Resample.command"), "w", encoding="utf-8") as fh:
    fh.write("Resample\n$Resample\nrebuild the voxel grid\n")
with open(os.path.join(MENU_DIR, "$SmoothObject.command"), "w", encoding="utf-8") as fh:
    fh.write("Smooth\n$SmoothObject\n")

FAKE = install_fake_coat(DOCS, COAT_SIDE)

# 3DCoat's own id table, in miniature: the prims we ship rows for, minus the two
# ids a real build does not have either (prm_TorusPrim / prm_ImagePrim - checked
# against 3DCoat 2025's English.xml). This is what a curated list is filtered by.
_LANG = os.path.join(DOCS, "3DCoat-Install", "data", "Languages")
os.makedirs(_LANG, exist_ok=True)
_PRIM_IDS = ["prm_SpherePrim", "prm_CubPrim", "prm_EllipsePrim", "prm_CylinderPrim",
             "prm_ConePrim", "prm_TubePrim", "prm_CapsulePrim", "prm_NGonPrim",
             "prm_LathePrim", "prm_TextPrim",
             "ffBlob", "ffCube", "ffCylinder", "ffTorus", "ffRing", "ffDisc",
             "ffPatch", "ffRound"]
with open(os.path.join(_LANG, "English.xml"), "w", encoding="utf-8") as fh:
    fh.write("<Language>\n")
    for _id in _PRIM_IDS:
        fh.write(f"\t<TextItem><ID>{_id}</ID><Text>{_id}</Text></TextItem>\n")
    fh.write("</Language>\n")

from coatmenu.core import menus_registry as registry  # noqa: E402
from coatmenu.core import presets  # noqa: E402
from coatmenu.core.config import MenuConfig, Menu, item_from_json, item_to_json, slugify, starter_config  # noqa: E402
from coatmenu.core.menu_model import (  # noqa: E402
    COMMAND, EXPAND_AUTO, EXPAND_MODES, SUBMENU, POSITION_MODES, MenuItem,
)

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== slugs and hotkey ids ==")
check(slugify("Sculpt") == "Sculpt", "ascii name kept as-is")
check(slugify("Sub D / Retopo") == "Sub_D_Retopo", "separators collapse to underscores")
check(slugify("硬表面").startswith("menu_"),
      f"a name outside ascii still becomes an ascii slug ({slugify('硬表面')})")
check(slugify("硬表面") == slugify("硬表面"), "the same name always gives the same slug")
check(slugify("硬表面") != slugify("雕刻"),
      f"two such names no longer collide ({slugify('硬表面')} / {slugify('雕刻')})")
check(slugify("Sculpt 硬表面").startswith("Sculpt_"),
      f"an ascii name with a tail keeps its readable part ({slugify('Sculpt 硬表面')})")
check(slugify("Sculpt 硬表面") != slugify("硬表面 Sculpt"),
      "names that only match outside ascii stay apart")
check(Menu(name="Sub D").hotkey_id == "CoatMenu_Sub_D", "hotkey id is namespaced")

print("== item forms ==")
check(item_from_json("Resample").cid == "Resample", "bare string is a command")
check(item_from_json({"id": "Bevel", "label": "Bevel tool"}).label == "Bevel tool", "id + label")
check(item_from_json({"script": "C:/x/y.py"}).path == "C:/x/y.py", "script entry")
check(item_from_json({"script": "C:/x/y.py"}).label == "y.py", "script label defaults to file name")
sub = item_from_json({"name": "Booleans", "items": ["SubtractVolume"], "dummy": 1})
check(sub.is_branch and sub.children[0].cid == "SubtractVolume", "submenu with children")
check(item_from_json({"separator": True}).kind == "separator", "separator")
check(item_from_json({"header": "Shading"}).kind == "header", "header")
check(item_from_json({"nonsense": 1}) is None, "unknown dict is dropped")
check(item_from_json("") is None, "empty string is dropped")

print("== round trip (old key included) ==")
# A file written before the terminology pass used "lists"; it still loads.
check(MenuConfig.from_json({"version": 1, "lists": [{"name": "Old", "items": ["Resample"]}]})
      .menus[0].name == "Old", "a config written with the old \"lists\" key still loads")
check("menus" in MenuConfig(menus=[Menu(name="New")]).to_json(),
      "and new files are written with the \"menus\" key")
config = MenuConfig.from_json(
    {
        "version": 1,
        "lists": [
            {
                "name": "Sculpt",
                "items": [
                    "Resample",
                    {"id": "Bevel", "label": "Bevel tool"},
                    {"script": "C:/x/y.py", "label": "Run y"},
                    {"name": "Booleans", "items": ["SubtractVolume"]},
                    {"separator": True},
                ],
            }
        ],
    }
)
again = MenuConfig.from_json(config.to_json())
check(json.dumps(config.to_json(), sort_keys=True) == json.dumps(again.to_json(), sort_keys=True),
      "to_json -> from_json is stable")
check(config.find("Sculpt") is config.menus[0], "find by name")
check(config.find("CoatMenu_Sculpt") is config.menus[0], "find by hotkey id")

print("== editing helpers ==")
config.add_menu("Sculpt")
check(config.menus[-1].name == "Sculpt 2", f"duplicate names are made unique ({config.menus[-1].name})")
check(config.move_menu("Sculpt 2", -1) is True, "list can move up")
check(config.rename_menu("Sculpt 2", "Retopo").name == "Retopo", "rename works")
removed = config.remove_menu("Retopo")
check(removed and config.find("Retopo") is None, "remove works")
check(config.remove_menu("Sculpt") is False,
      "the last list cannot be removed (a config always has one list)")

print("== starter config is the shipped set, built for this build ==")
starter = starter_config(DOCS)
check([lst.name for lst in starter.menus] == list(presets.DEFAULT_LISTS),
      f"the first run gets the lists we ship ({[lst.name for lst in starter.menus]})")
check(all(lst.preset for lst in starter.menus),
      "each one carries its preset marker")
check(any(item.kind == "command" for lst in starter.menus for item in lst.items),
      "and the rows are real commands, not placeholders")

print("== save / load ==")
cfg_path = os.path.join(tempfile.mkdtemp(prefix="coatmenu-cfg-"), "lists.json")
starter.save(cfg_path)
loaded = MenuConfig.load(cfg_path)
check([lst.name for lst in loaded.menus] == [lst.name for lst in starter.menus], "save -> load keeps lists")
check(MenuConfig.load(os.path.join(os.path.dirname(cfg_path), "missing.json")).menus,
      "missing file falls back to the starter config")

print("== launcher scripts + menu xml ==")
ext = tempfile.mkdtemp(prefix="coatmenu-ext-")
entry_dir = os.path.join(ext, "actions", "menus")
xml_path = os.path.join(tempfile.mkdtemp(prefix="coatmenu-xml-"), "CoatMenu.xml")
cfg = MenuConfig(menus=[Menu(name="Sculpt"), Menu(name="Paint")])
info = registry.sync(cfg, ext, entry_dir, xml_path)
check(info["menus"] == 2, "sync reports the menu count")

sculpt_script = registry.entry_script_path(entry_dir, "Sculpt")
check(os.path.isfile(sculpt_script), "launcher script written per list")
with open(sculpt_script, encoding="utf-8") as fh:
    source = fh.read()
check("show_list('Sculpt'" in source, "launcher calls show_list with its slug")
check("def main()" in source and "\nmain()\n" in source, "launcher is unconditional (no __name__ guard)")
check("if __name__" not in source, "no __name__ guard in the generated launcher")
check("_schedule_self_removal" in source,
      "launcher un-registers itself so a second click runs again")

with open(xml_path, encoding="utf-8") as fh:
    xml = fh.read()
check(xml.count("<ExtraMenuItem>") == 3,
      f"the XML holds only the three fixed entries ({xml.count('<ExtraMenuItem>')})")
check("<MenuItem>CoatMenu_Show</MenuItem>" in xml, "main entry registered")
check("<MenuItem>CoatMenu_Editor</MenuItem>" in xml, "editor entry registered")
check("<MenuItem>CoatMenu_Doctor</MenuItem>" in xml, "doctor entry registered")
# The one-per-menu entries moved to the runtime API - that is what lets them carry
# a hotkey; writing them in both places would list every menu twice.
check("<MenuItem>CoatMenu_Sculpt</MenuItem>" not in xml,
      "menu entries are no longer in the XML")
menu_rows = registry.menu_entries(cfg, ext, entry_dir, include="menus")
check(len(menu_rows) == len(cfg.menus),
      f"the API side gets one entry per menu ({len(menu_rows)})")
check(menu_rows[0][0] == "CoatMenu_Sculpt", "with the id 3DCoat knows it by")
check(menu_rows[0][2] == sculpt_script, "and its launcher script")

print("== Scripts menu entries are prefixed ==")
entries = registry.menu_entries(cfg, ext, entry_dir)
labels = {menu_id: label for menu_id, label, _script in entries}
check(labels["CoatMenu_Sculpt"] == "CoatMenu_Sculpt",
      f"a menu's Scripts entry carries the prefix ({labels['CoatMenu_Sculpt']})")
check(labels["CoatMenu_Show"] == "Show CoatMenu", "the main entry keeps its own name")
check(labels["CoatMenu_Editor"] == "Edit menus", "and so does the editor entry")
check(registry.entry_label("Shade  (3)") == "CoatMenu_Shade (3)",
      "double spaces are squeezed out of the label")
check(registry.legacy_hotkey_ids(cfg) == ["CoatMenu_List_Sculpt", "CoatMenu_List_Paint"],
      f"the ids the previous version used are known ({registry.legacy_hotkey_ids(cfg)})")

print("== two menus whose names are not ascii get one entry each ==")
cjk = MenuConfig(menus=[Menu(name="硬表面"), Menu(name="雕刻")])
pairs = registry.menu_slugs(cjk)
check(len({slug for slug, _menu in pairs}) == 2,
      f"one slug each ({[slug for slug, _m in pairs]})")
cjk_rows = registry.menu_entries(cjk, ext, entry_dir, include="menus")
check(len({menu_id for menu_id, _label, _script in cjk_rows}) == 2,
      f"and one id each ({[row[0] for row in cjk_rows]})")
cjk_dir = tempfile.mkdtemp(prefix="coatmenu-cjk-")
registry.write_entry_scripts(cjk, cjk_dir)
check(len([n for n in os.listdir(cjk_dir) if n.endswith(".py")]) == 2,
      f"both launcher files are written ({sorted(os.listdir(cjk_dir))})")

print("== a path with '&' does not break the file 3DCoat reads ==")
# 3DCoat refuses a file whose XML is malformed, and '&' in a path (an account
# called "Ben & Jerry", a folder called "R&D") is what made ours malformed.
amp_ext = os.path.join(tempfile.mkdtemp(prefix="coatmenu-amp-"), "R&D")
amp_entry = os.path.join(amp_ext, "actions", "menus")
amp_xml = os.path.join(amp_ext, "ExtraMenuItems", "CoatMenu.xml")
registry.sync(MenuConfig(menus=[Menu(name="Sculpt")]), amp_ext, amp_entry, amp_xml)
import xml.etree.ElementTree as ET  # noqa: E402

amp_tree = ET.parse(amp_xml)
amp_commands = [node.text or "" for node in amp_tree.iter("Command")]
check(len(amp_commands) == 3, f"the three fixed entries parse ({len(amp_commands)})")
check(all(cmd.startswith("script:") and "R&D" in cmd for cmd in amp_commands),
      f"the absolute path survived escaping ({amp_commands[0]})")
with open(amp_xml, encoding="utf-8") as fh:
    amp_text = fh.read()
check("&amp;" in amp_text and "R&D" not in amp_text,
      "the '&' is written as an entity, not raw")

print("== stale launchers are cleaned up ==")
cfg2 = MenuConfig(menus=[Menu(name="Sculpt")])
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_removed"], f"removed stale launcher ({info['scripts_removed']})")
check(not os.path.exists(registry.entry_script_path(entry_dir, "Paint")), "Paint launcher is gone")

print("== re-sync does not rewrite unchanged launchers ==")
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_written"] == [], "no needless rewrite")

print("== the Add preset (3DCoat's own primitives, filtered at build time) ==")
from coatmenu.core.menu_model import flatten  # noqa: E402

groups = presets.primitive_groups()
check([len(rows) for _label, rows in groups] == [10, 8],
      f"two groups, 10/8 entries ({[len(r) for _l, r in groups]})")
check([label for label, _rows in groups] == ["Built-in Prims\u2026", "FFD Prims\u2026"],
      f"and no Mesh Prims group ({[label for label, _rows in groups]}) - the files "
      f"it pointed at are not in 3DCoat")

preset_list = presets.primitives_list()
check(preset_list.name == "Add", f"the list is called Add ({preset_list.name})")
check(preset_list.mode == "list", f"opens as a list ({preset_list.mode})")
kinds = [i.kind for i in preset_list.items]
check(kinds[:10] == ["command"] * 10,
      "the built-in shapes sit straight on the list (no submenu)")
check(kinds[10] == "separator", "then a separator")
check(kinds[11:] == ["submenu"], "and the FFD shapes stay folded into a submenu")
check(len(preset_list.items) == 12, f"12 rows in total ({len(preset_list.items)})")

labels = [i.label for i in preset_list.items[:10]]
check(labels == ["Sphere", "Cube", "Ellipse", "Cylinder", "Cone", "Tube", "Capsule",
                 "NGon", "Lathe", "Text"],
      f"an id this build does not define is left out ({labels})")

sphere = preset_list.items[0]
check(sphere.label == "Sphere", f"first row is the built-in Sphere ({sphere.label})")
check(sphere.cmds == ["$SCULPT_TRANSFORM", "$SCULP_PRIM",
                      "$VoxelSculptTool::prm_SpherePrim"],
      f"three-step sequence, same order 3DCoat needs ({sphere.cmds})")
check(preset_list.items[1].cmds[-1] == "$VoxelSculptTool::prm_CubPrim",
      "Cube keeps 3DCoat's own abbreviation (prm_CubPrim)")
check(preset_list.items[11].children[0].cmds[-1] == "$VoxelSculptTool::ffBlob",
      "FFD entry uses the ff* id")
check(not any("$select_" in (item.cid or "") for item in flatten(preset_list.items)),
      "no row runs the $select_* command form nothing verified")

preset_cfg = MenuConfig()
check(presets.install_presets(preset_cfg, names=("Add",)) == ["Add"], "preset list added")
check(preset_cfg.find("Add").preset == "prims/2",
      f"a shipped list carries its version marker ({preset_cfg.find('Add').preset})")
check(presets.install_presets(preset_cfg, names=("Add",)) == [],
      "adding it twice does nothing")

older = MenuConfig(menus=[Menu(name="Add", preset="prims/1")])
check(presets.install_presets(older, names=("Add",)) == [],
      "a shipped list from an older version is not refreshed either")
check(older.find("Add").items == [] and older.find("Add").preset == "prims/1",
      "it keeps exactly what it has - no new rows, no marker bump")

# A menu we shipped is the user's from the moment it is in his file, and his
# "custom" menus *are* today's shipped defaults. An update may add a list that is
# missing; nothing that exists is edited, reordered or rewritten.
_three = ["$SCULPT_TRANSFORM", "$SCULP_PRIM", "$VoxelSculptTool::prm_SpherePrim"]
edited = MenuConfig(menus=[Menu(name="Add Prims", preset="prims/1", items=[
    MenuItem(label="Sphere", kind=COMMAND, cid="$SCULPT_TRANSFORM", cmds=list(_three)),
    MenuItem(label="My Booleans", kind=COMMAND, cid="MyBoolean"),
])])
_before = list(edited.find("Add Prims").items)
check(presets.install_presets(edited, names=("Add",)) == [],
      "an edited built-in is left alone")
_menu = edited.find("Add Prims")
check(_menu is not None and _menu.name == "Add Prims",
      "a renamed built-in is found by its marker, not its name")
check(_menu.items == _before, "his rows are exactly as he left them")
check(len(_menu.items) == 2, f"and nothing was added to them ({len(_menu.items)})")
check(_menu.preset == "prims/1", "not even the marker is rewritten")

# A list that really is missing is still added - that changes nothing that exists.
_partly = MenuConfig(menus=[Menu(name="Add", preset="prims/2", items=[])])
check(presets.install_presets(_partly, names=("Add", "Tools")) == ["Tools"],
      "only a genuinely missing list is installed")
check(_partly.find("Add").items == [], "and the one that exists is untouched")
check(len(_partly.menus) == 2, f"the missing one landed ({[m.name for m in _partly.menus]})")

handmade = MenuConfig(menus=[Menu(name="Add", items=[MenuItem(label="Mine", cid="MINE")])])
check(presets.install_presets(handmade, names=("Add",)) == [],
      "a hand-built list with the same name is left alone")
check(len(handmade.find("Add").items) == 1, "and keeps its own rows")

tools_cfg = MenuConfig()
check(presets.install_presets(tools_cfg, names=("Tools",)) == ["Tools"],
      "the Tools preset (your CustomTools) installs alongside Add")
check(tools_cfg.find("Tools").preset == "tools/1", "with a marker of its own")

round_trip = MenuConfig.from_json(preset_cfg.to_json())
back = round_trip.find("Add").items[0]
check(back.cmds == sphere.cmds, f"sequences survive a JSON round trip ({back.cmds})")
check(round_trip.find("Add").preset == "prims/2", "the preset marker survives too")
check(isinstance(round_trip.to_json()["menus"][0]["items"][0], dict),
      "a multi-command row is written as an object, not a bare id")

saved_cfg = MenuConfig(menus=[Menu(name="Saved", items=[
    MenuItem(label="HS_Extrude", kind="preset", cid="HS_Extrude")])])
saved_json = saved_cfg.to_json()["menus"][0]["items"][0]
check(saved_json == {"preset": "HS_Extrude", "label": "HS_Extrude"},
      f"a preset row still writes as {{preset: ...}} ({saved_json})")
# Tool presets cannot be activated on this build (the documented API does not
# exist), so the loader drops them rather than turning them into a $command that
# can never resolve. A config written by an older build therefore just loses that
# one menu, and works otherwise.
saved_menu = MenuConfig.from_json(saved_cfg.to_json()).find("Saved")
check(saved_menu is not None and not saved_menu.items,
      f"and a preset row is dropped on load ({saved_menu.items if saved_menu else None})")
check(MenuConfig.from_json(saved_cfg.to_json()).find("Saved") is not None,
      "the menu itself survives")

print("== key bindings, clashes and the doctor report ==")
from coatmenu.core import bindings as bindings_mod  # noqa: E402
from coatmenu.core import doctor  # noqa: E402
from coatmenu.core import show as show_mod  # noqa: E402

hotkeys_file = os.path.join(DOCS, "3DCoat", "UserPrefs", "Preferences", "Options_Hotkeys.xml")
os.makedirs(os.path.dirname(hotkeys_file), exist_ok=True)
bind_cfg = MenuConfig(menus=[
    Menu(name="Sculpt"),
    Menu(name="Paint"),
    Menu(name="Prims"),
])
with open(hotkeys_file, "w", encoding="utf-8") as fh:
    fh.write(
        '<AppOptions><HotKeys>\n'
        '\t<OneHotKey><ID>CoatMenu_Sculpt</ID><Room>Voxels</Room><Code>Q</Code>'
        '<Ctrl>true</Ctrl></OneHotKey>\n'
        '\t<OneHotKey><ID>CoatMenu_Paint</ID><Room>Voxels</Room><Code>Q</Code>'
        '<Ctrl>true</Ctrl></OneHotKey>\n'
        '\t<OneHotKey><ID>CoatMenu_Prims</ID><Room>Voxels</Room><Code>key_00</Code>'
        '</OneHotKey>\n'
        '</HotKeys></AppOptions>\n'
    )
seen = bindings_mod.describe(bind_cfg, hotkeys_file)
check(seen.for_menu("Sculpt") == "Ctrl+Q", f"binding read as Ctrl+Q ({seen.for_menu('Sculpt')})")
check(seen.for_menu("Prims") == "", "an unbound list reports nothing")
check(len(seen.conflicts) == 1 and "Sculpt" in seen.conflicts[0],
      f"two lists on one key are flagged ({seen.conflicts})")
check(bindings_mod.key_label("key_00") == "", "the unbound placeholder has no label")
check(bindings_mod.key_label("ENTER") == "Enter", "named keys get readable labels")

text = doctor.report(bind_cfg)
check("CoatMenu doctor" in text, "the doctor writes a titled report")
check("Sculpt" in text and "Ctrl+Q" in text, "the report lists lists and their keys")
check("command source:" in text, "the report includes the catalog sizes")
check(doctor.startup_path().endswith("startup.txt"), "the doctor knows the startup file")

empty = Menu(name="Nothing")
rows = show_mod.list_rows(empty)
check(len(rows) == 1 and rows[0].kind == "header",
      f"an empty list opens a hint row instead of nothing ({rows[0].kind})")
filled = Menu(name="Some", items=[MenuItem(label="A", cid="A")])
check(len(show_mod.list_rows(filled)) == 1 and show_mod.list_rows(filled)[0].label == "A",
      "a filled list is passed through untouched")

print("== a row's expand mode survives the config ==")
for mode in EXPAND_MODES:
    row = MenuItem(label="G", kind=SUBMENU, expand=mode,
                              children=[MenuItem(label="c", kind=COMMAND, cid="c")])
    body = item_to_json(row)
    back = item_from_json(body)
    check(back.expand == mode, f"{mode} round trips ({back.expand})")
check("expand" not in item_to_json(
    MenuItem(label="G", kind=SUBMENU,
                        children=[MenuItem(label="c", kind=COMMAND, cid="c")])),
    "auto is left out, so the file stays as short as it was")

print("== a row's pie position survives the config ==")
for spot in POSITION_MODES:
    row = MenuItem(label="G", kind=SUBMENU, position=spot,
                   children=[MenuItem(label="c", kind=COMMAND, cid="c")])
    back = item_from_json(item_to_json(row))
    check(back.position == spot, f"{spot} round trips ({back.position})")
_plain = MenuItem(label="G", kind=SUBMENU,
                  children=[MenuItem(label="c", kind=COMMAND, cid="c")])
check("where" not in item_to_json(_plain), "auto is left out of the file")

print("== a renamed built-in menu is recognised by its marker ==")
# The bug: install_presets looked menus up by name, so renaming a shipped menu
# (Add -> My Prims) made it install a second copy beside the user's.
renamed = MenuConfig(menus=[
    Menu(name="My Prims", preset="prims/2", items=[
        MenuItem(label="Cube", kind=COMMAND, cid="prm_CubPrim")]),
])
presets.install_presets(renamed)
_names = [m.name for m in renamed.menus]
check("Add" not in _names, f"no duplicate Add is installed ({_names})")
check(len(renamed.find("My Prims").items) == 1,
      "and the renamed menu keeps its own rows")

# A hand-built menu has no marker: it must be left alone, and must not stop the
# built-ins from installing.
mine = MenuConfig(menus=[Menu(name="My Stuff", items=[
    MenuItem(label="mine", kind=COMMAND, cid="x")])])
presets.install_presets(mine)
_names = [m.name for m in mine.menus]
check("My Stuff" in _names, "a hand-built menu is never touched")
check([name for name in presets.DEFAULT_LISTS if name in _names] == list(presets.DEFAULT_LISTS),
      f"and every shipped list still installs ({_names})")

print("== a config we cannot read is moved aside, never replaced ==")
# The panel-side half of the same rule: a starter written over his file is data
# loss on a file that is usually repairable, so it is renamed instead.
from coatmenu.core import config as config_mod  # noqa: E402

_broken_dir = tempfile.mkdtemp(prefix="coatmenu-broken-")
_broken = os.path.join(_broken_dir, "menus.json")
_broken_text = '{"version": 1, "menus": [ {oops\n'
with open(_broken, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(_broken_text)
check(not config_mod.config_readable(_broken), "an unreadable config is recognised as such")
_moved = config_mod.quarantine_unreadable(_broken, stamp="test")
check(_moved == _broken + ".unreadable-test", f"it is renamed, not deleted ({os.path.basename(_moved)})")
with open(_moved, encoding="utf-8") as fh:
    check(fh.read() == _broken_text, "and keeps its bytes exactly")
check(not os.path.exists(_broken), "the canonical path is left free for the next save")
check(config_mod.quarantine_unreadable(_broken) == "", "nothing to move when there is no file")

_healthy = os.path.join(_broken_dir, "healthy.json")
with open(_healthy, "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"version": 1, "menus": [{"name": "Mine", "items": []}]}, fh)
check(config_mod.config_readable(_healthy), "a readable config is readable")
check(config_mod.quarantine_unreadable(_healthy) == "", "and is never moved")
check(config_mod.unreadable_copies(_healthy) == [], "nothing is listed when nothing was moved")
check(config_mod.unreadable_copies(_broken) == [_moved],
      "while a kept copy is listed next to where it came from")

_keep_env = os.environ.get("COATMENU_DATA_DIR")
os.environ["COATMENU_DATA_DIR"] = _broken_dir
check(doctor.config_line().startswith("MISSING"), "the doctor says when there is no config")
with open(_broken, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(_broken_text)
check("UNREADABLE" in doctor.config_line(),
      f"and shouts about one it cannot read ({doctor.config_line()})")
with open(_broken, "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"version": 1, "menus": [{"name": "Mine", "items": []}]}, fh)
check("unreadable copy" in doctor.config_line(),
      f"and mentions a copy it kept ({doctor.config_line()})")
if _keep_env is None:
    os.environ.pop("COATMENU_DATA_DIR", None)
else:
    os.environ["COATMENU_DATA_DIR"] = _keep_env

print()
if failures:
    print(f"CONFIG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CONFIG REGRESSION PASSED")
sys.exit(0)
