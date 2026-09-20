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

from coatmenu.core import menus_registry as registry  # noqa: E402
from coatmenu.core.config import MenuConfig, Menu, item_from_json, item_to_json, slugify, starter_config  # noqa: E402
from coatmenu.core.menu_model import MenuItem  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== slugs and hotkey ids ==")
check(slugify("Sculpt") == "Sculpt", "ascii name kept as-is")
check(slugify("Sub D / Retopo") == "Sub_D_Retopo", "separators collapse to underscores")
check(slugify("硬表面") == "menu", "non-ascii name falls back to 'menu'")
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

print("== round trip ==")
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

print("== starter config uses real CustomMenu entries ==")
starter = starter_config(DOCS)
check(len(starter.menus) >= 1, f"starter has {len(starter.menus)} list(s)")
check(any(item.cid == "Resample" for item in starter.menus[0].items),
      f"starter built from CustomMenu ({[i.cid for i in starter.menus[0].items]})")

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
check(xml.count("<ExtraMenuItem>") == 5,
      f"main entry + editor + doctor + one per list ({xml.count('<ExtraMenuItem>')})")
check("<MenuItem>CoatMenu_Show</MenuItem>" in xml, "main entry registered")
check("<MenuItem>CoatMenu_Editor</MenuItem>" in xml, "editor entry registered")
check("<MenuItem>CoatMenu_Doctor</MenuItem>" in xml, "doctor entry registered")
check("<MenuItem>CoatMenu_Sculpt</MenuItem>" in xml, "list entry registered")
check(f"<Command>script:{registry._posix(sculpt_script)}</Command>" in xml, "absolute posix script path")

print("== stale launchers are cleaned up ==")
cfg2 = MenuConfig(menus=[Menu(name="Sculpt")])
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_removed"], f"removed stale launcher ({info['scripts_removed']})")
check(not os.path.exists(registry.entry_script_path(entry_dir, "Paint")), "Paint launcher is gone")

print("== re-sync does not rewrite unchanged launchers ==")
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_written"] == [], "no needless rewrite")

print("== built-in Prims preset (port of the LKS Add-Prims menu) ==")
from coatmenu.core import presets  # noqa: E402

groups = presets.primitive_groups()
check([len(rows) for _label, rows in groups] == [12, 5, 8],
      f"three groups, 12/5/8 entries ({[len(r) for _l, r in groups]})")

preset_list = presets.primitives_list()
check(preset_list.mode == "list", f"opens as a list ({preset_list.mode})")
kinds = [i.kind for i in preset_list.items]
check(kinds[:12] == ["command"] * 12,
      "the built-in shapes sit straight on the list (no submenu)")
check(kinds[12] == "separator", "then a separator")
check(kinds[13:] == ["submenu", "submenu"], "mesh and FFD stay folded into submenus")
check(len(preset_list.items) == 15, f"15 rows in total ({len(preset_list.items)})")

sphere = preset_list.items[0]
check(sphere.label == "Sphere", f"first row is the built-in Sphere ({sphere.label})")
check(sphere.cmds == ["$SCULPT_TRANSFORM", "$SCULP_PRIM",
                      "$VoxelSculptTool::prm_SpherePrim"],
      f"three-step sequence, same order 3DCoat needs ({sphere.cmds})")
check(preset_list.items[1].cmds[-1] == "$VoxelSculptTool::prm_CubPrim",
      "Cube keeps 3DCoat's own abbreviation (prm_CubPrim)")

mesh = preset_list.items[13].children[0]
check(mesh.cmds == ["$SCULPT_TRANSFORM", "$SCULP_MERGE",
                    "$select_UserPrefs/Models/SculptModels/Cube.obj"],
      f"mesh prims go through the merge tool ({mesh.cmds})")
check(preset_list.items[14].children[0].cmds[-1] == "$VoxelSculptTool::ffBlob",
      "FFD entry uses the ff* id")

preset_cfg = MenuConfig()
check(presets.install_presets(preset_cfg, names=("Prims",)) == ["Prims"], "preset list added")
check(preset_cfg.find("Prims").preset == "prims/2",
      f"a shipped list carries its version marker ({preset_cfg.find('Prims').preset})")
check(presets.install_presets(preset_cfg, names=("Prims",)) == [],
      "adding it twice does nothing")

older = MenuConfig(menus=[Menu(name="Prims", preset="prims/1")])
check(presets.install_presets(older, names=("Prims",)) == ["Prims (refreshed)"],
      "an older shipped version is refreshed in place")
check(len(older.find("Prims").items) == 15, "and gets the current rows")

handmade = MenuConfig(menus=[Menu(name="Prims", items=[MenuItem(label="Mine", cid="MINE")])])
check(presets.install_presets(handmade, names=("Prims",)) == [],
      "a hand-built list with the same name is left alone")
check(len(handmade.find("Prims").items) == 1, "and keeps its own rows")

tools_cfg = MenuConfig()
check(presets.install_presets(tools_cfg, names=("Tools",)) == ["Tools"],
      "the Tools preset (your CustomTools) installs alongside Prims")
check(tools_cfg.find("Tools").preset == "tools/1", "with a marker of its own")

round_trip = MenuConfig.from_json(preset_cfg.to_json())
back = round_trip.find("Prims").items[0]
check(back.cmds == sphere.cmds, f"sequences survive a JSON round trip ({back.cmds})")
check(round_trip.find("Prims").preset == "prims/2", "the preset marker survives too")
check(isinstance(round_trip.to_json()["lists"][0]["items"][0], dict),
      "a multi-command row is written as an object, not a bare id")

saved_cfg = MenuConfig(menus=[Menu(name="Saved", items=[
    MenuItem(label="HS_Extrude", kind="preset", cid="HS_Extrude")])])
saved_json = saved_cfg.to_json()["lists"][0]["items"][0]
check(saved_json == {"preset": "HS_Extrude", "label": "HS_Extrude"},
      f"a saved preset is written as {{preset: ...}} ({saved_json})")
saved_back = MenuConfig.from_json(saved_cfg.to_json()).find("Saved").items[0]
check(saved_back.kind == "preset" and saved_back.cid == "HS_Extrude",
      "and comes back as a runnable preset entry")
check(saved_back.clickable, "so the row can actually be clicked")

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

print()
if failures:
    print(f"CONFIG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CONFIG REGRESSION PASSED")
sys.exit(0)
