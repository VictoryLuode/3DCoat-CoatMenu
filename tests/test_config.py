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

from core import lists_registry as registry  # noqa: E402
from core.config import MenuConfig, MenuList, item_from_json, item_to_json, slugify, starter_config  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== slugs and hotkey ids ==")
check(slugify("Sculpt") == "Sculpt", "ascii name kept as-is")
check(slugify("Sub D / Retopo") == "Sub_D_Retopo", "separators collapse to underscores")
check(slugify("硬表面") == "list", "non-ascii name falls back to 'list'")
check(MenuList(name="Sub D").hotkey_id == "CoatMenu_List_Sub_D", "hotkey id is namespaced")

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
check(config.find("Sculpt") is config.lists[0], "find by name")
check(config.find("CoatMenu_List_Sculpt") is config.lists[0], "find by hotkey id")

print("== editing helpers ==")
config.add_list("Sculpt")
check(config.lists[-1].name == "Sculpt 2", f"duplicate names are made unique ({config.lists[-1].name})")
check(config.move_list("Sculpt 2", -1) is True, "list can move up")
check(config.rename_list("Sculpt 2", "Retopo").name == "Retopo", "rename works")
removed = config.remove_list("Retopo")
check(removed and config.find("Retopo") is None, "remove works")
check(config.remove_list("Sculpt") is False,
      "the last list cannot be removed (a config always has one list)")

print("== starter config uses real CustomMenu entries ==")
starter = starter_config(DOCS)
check(len(starter.lists) >= 1, f"starter has {len(starter.lists)} list(s)")
check(any(item.cid == "Resample" for item in starter.lists[0].items),
      f"starter built from CustomMenu ({[i.cid for i in starter.lists[0].items]})")

print("== save / load ==")
cfg_path = os.path.join(tempfile.mkdtemp(prefix="coatmenu-cfg-"), "lists.json")
starter.save(cfg_path)
loaded = MenuConfig.load(cfg_path)
check([lst.name for lst in loaded.lists] == [lst.name for lst in starter.lists], "save -> load keeps lists")
check(MenuConfig.load(os.path.join(os.path.dirname(cfg_path), "missing.json")).lists,
      "missing file falls back to the starter config")

print("== launcher scripts + menu xml ==")
ext = tempfile.mkdtemp(prefix="coatmenu-ext-")
entry_dir = os.path.join(ext, "actions", "lists")
xml_path = os.path.join(tempfile.mkdtemp(prefix="coatmenu-xml-"), "CoatMenu.xml")
cfg = MenuConfig(lists=[MenuList(name="Sculpt"), MenuList(name="Paint")])
info = registry.sync(cfg, ext, entry_dir, xml_path)
check(info["lists"] == 2, "sync reports the list count")

sculpt_script = registry.entry_script_path(entry_dir, "Sculpt")
check(os.path.isfile(sculpt_script), "launcher script written per list")
with open(sculpt_script, encoding="utf-8") as fh:
    source = fh.read()
check("show_list('Sculpt'" in source, "launcher calls show_list with its slug")
check("def main()" in source and "\nmain()\n" in source, "launcher is unconditional (no __name__ guard)")
check("if __name__" not in source, "no __name__ guard in the generated launcher")

with open(xml_path, encoding="utf-8") as fh:
    xml = fh.read()
check(xml.count("<ExtraMenuItem>") == 4,
      f"main entry + editor + one per list ({xml.count('<ExtraMenuItem>')})")
check("<MenuItem>CoatMenu_Show</MenuItem>" in xml, "main entry registered")
check("<MenuItem>CoatMenu_Editor</MenuItem>" in xml, "editor entry registered")
check("<MenuItem>CoatMenu_List_Sculpt</MenuItem>" in xml, "list entry registered")
check(f"<Command>script:{registry._posix(sculpt_script)}</Command>" in xml, "absolute posix script path")

print("== stale launchers are cleaned up ==")
cfg2 = MenuConfig(lists=[MenuList(name="Sculpt")])
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_removed"], f"removed stale launcher ({info['scripts_removed']})")
check(not os.path.exists(registry.entry_script_path(entry_dir, "Paint")), "Paint launcher is gone")

print("== re-sync does not rewrite unchanged launchers ==")
info = registry.sync(cfg2, ext, entry_dir, xml_path)
check(info["scripts_written"] == [], "no needless rewrite")

print()
if failures:
    print(f"CONFIG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CONFIG REGRESSION PASSED")
sys.exit(0)
