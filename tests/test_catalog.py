"""
Catalog + hotkey parsing tests - pure filesystem, no Qt.

Run:  python tests/test_catalog.py
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
sys.path.insert(0, HERE)
sys.path.insert(0, COAT_SIDE)

from fake_coat import install_fake_coat  # noqa: E402

DOCS = tempfile.mkdtemp(prefix="coatmenu-catalog-")
USERPREF = os.path.join(DOCS, "3DCoat", "UserPrefs")
os.makedirs(os.path.join(USERPREF, "Preferences"), exist_ok=True)
os.makedirs(os.path.join(USERPREF, "CustomMenu", "VoxelsCustom", "Shading"), exist_ok=True)
os.makedirs(os.path.join(USERPREF, "Scripts", "sub"), exist_ok=True)

HOTKEYS = os.path.join(USERPREF, "Preferences", "Options_Hotkeys.xml")
with open(HOTKEYS, "w", encoding="utf-8") as fh:
    fh.write("""<AppOptions>
\t<HotKeys>
\t\t<OneHotKey><ID>UNDO</ID><Room>Voxels</Room><Code>Z</Code><Ctrl>true</Ctrl><Alt>false</Alt><Shift>false</Shift></OneHotKey>
\t\t<OneHotKey><ID>REDO</ID><Room>Voxels</Room><Code>key_00</Code><Ctrl>false</Ctrl><Alt>false</Alt><Shift>true</Shift></OneHotKey>
\t\t<OneHotKey><ID>VIEW_WIREFRAME</ID><Room></Room><Code>F4</Code><Ctrl>false</Ctrl><Alt>false</Alt><Shift>false</Shift></OneHotKey>
\t\t<OneHotKey><ID>CoatMenu_Show</ID><Room></Room><Code>Q</Code><Ctrl>false</Ctrl><Alt>true</Alt><Shift>false</Shift></OneHotKey>
\t\t<OneHotKey><ID>execute:C:/t/actions/CoatMenu_Show.py</ID><Room></Room><Code>key_00</Code><Ctrl>false</Ctrl><Alt>false</Alt><Shift>false</Shift></OneHotKey>
\t</HotKeys>
</AppOptions>
""")

with open(os.path.join(USERPREF, "CustomMenu", "VoxelsCustom", "$Resample.command"),
          "w", encoding="utf-8") as fh:
    fh.write("Resample\n$Resample\nRecompute the voxel grid\n")
with open(os.path.join(USERPREF, "CustomMenu", "VoxelsCustom", "Shading", "$VIEW_SHADED.command"),
          "w", encoding="utf-8") as fh:
    fh.write("Shaded\n$VIEW_SHADED\n")
with open(os.path.join(USERPREF, "Scripts", "speedup.py"), "w", encoding="utf-8") as fh:
    fh.write("# demo\n")
with open(os.path.join(USERPREF, "Scripts", "sub", "helper.py"), "w", encoding="utf-8") as fh:
    fh.write("# demo\n")

# A stand-in for the 3DCoat program folder: its own menu definitions plus the
# English.xml name table (both live there, and neither can be corrupted).
INSTALL = tempfile.mkdtemp(prefix="coatmenu-install-")
CMAKE = os.path.join(INSTALL, "UserPrefs", "StdScripts", "cTemplates")
os.makedirs(os.path.join(CMAKE, "MainMenu"), exist_ok=True)
with open(os.path.join(CMAKE, "MainMenu", "File.py"), "w", encoding="utf-8") as fh:
    fh.write(
        'import coat\n'
        'from cTemplates.Structs import *\n\n'
        'CreateFileMenu = MainMenu("FILE")\n\n'
        '@d_menu_section(CreateFileMenu)\n'
        'def S_New():\n'
        '    coat.menu_item("CLEARSCENE")  # New\n'
        '    coat.menu_item("OPEN_FILE")   # Open\n'
        '    # coat.menu_item("COMMENTED_OUT")\n'
    )
with open(os.path.join(CMAKE, "MainMenu", "Edit.py"), "w", encoding="utf-8") as fh:
    fh.write('coat.menu_item("UNDO")  # Undo\n'
             'coat.menu_item("TRANSFORM_TRANSLATE_X")  # Move along the X-axis\n')
with open(os.path.join(CMAKE, "sculptTools.py"), "w", encoding="utf-8") as fh:
    fh.write(
        'import coat\n'
        'coat.menu_item("BaseVoxBrush")\n'
        'coat.menu_item("CLEARSCENE")\n'
        '\n'
        '@d_tools_section("Clay/Draw")\n'
        'def BaseSurfaceTools():\n'
        '    coat.tools_item("[extension]SCULP_SCLAY")  # Clay\n'
        '    coat.tools_item("{FLT}[extension]SCULP_PLANE")  # Flatten\n'
        '    # coat.tools_item("[extension]COMMENTED_TOOL")\n'
        '\n'
        '@d_tools_section("Layers")\n'
        'def Layers():\n'
        '    coat.tools_item("[extension]MagnifyLayers")  # Magnify SL\n'
        '    coat.tools_item("[extension]BendVolume")  # Array/Bend Volume\n'
    )
# The user's own tool presets: 3DCoat names each file after the tool it customises.
os.makedirs(os.path.join(USERPREF, "CustomTools"), exist_ok=True)
for tool in ("SCULP_SCLAY", "MagnifyLayers", "BendVolume", "SomePersonalTool"):
    with open(os.path.join(USERPREF, "CustomTools", f"{tool}.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(f"<CustomExtension><Name>{tool}</Name></CustomExtension>\n")

# Saved presets (the Presets panel), including 3DCoat's non-ASCII file naming.
PRESETS_DIR = os.path.join(USERPREF, "Presets")
os.makedirs(PRESETS_DIR, exist_ok=True)
with open(os.path.join(PRESETS_DIR, "HS_Extrude.xml"), "w", encoding="utf-8") as fh:
    fh.write("<OnePreset><Name>HS_Extrude</Name></OnePreset>\n")
with open(os.path.join(PRESETS_DIR, "HS_E58886E5B182Split.xml"), "w",
          encoding="utf-8") as fh:
    fh.write("<OnePreset><Name>HS_分层Split</Name></OnePreset>\n")
with open(os.path.join(PRESETS_DIR, "order.txt"), "w", encoding="utf-8") as fh:
    fh.write("HS_Extrude.xml\nHS_E58886E5B182Split.xml\n")

# A stand-in for the LKS extension's radial menus, which CoatMenu imports.
LKS_ROOT = os.path.join(USERPREF, "Scripts", "cExtensions", "LKS")
LKS_MENUS = os.path.join(LKS_ROOT, "data", "library", "radial_menus")
os.makedirs(os.path.join(LKS_ROOT, "actions"), exist_ok=True)
os.makedirs(LKS_MENUS, exist_ok=True)
with open(os.path.join(LKS_MENUS, "LKS_Radial_Booleans.json"), "w", encoding="utf-8") as fh:
    fh.write('{"version": 3, "name": "LKS_Radial_Booleans", "items": ['
             '{"label": "Apply", "type": "action", "action": "$LKS_Apply"},'
             '{"label": "New", "type": "list", "children": ['
             '{"label": "Union", "type": "action", "action": "$LKS_Union"}]},'
             '{"label": "Ghost", "type": "action", "action": "actions/Ghost.py"},'
             '{"label": "action", "type": "action"},'
             '{"label": "Decimate", "type": "action", "action": "ops.Decimate.main"}]}\n')
with open(os.path.join(LKS_MENUS, "Shift S.json"), "w", encoding="utf-8") as fh:
    fh.write('{"version": 3, "name": "Shift S", "items": ['
             '{"label": "Reset Axis", "type": "action", "action": "$Reset Axis"}]}\n')
with open(os.path.join(LKS_MENUS, "Alt Q.json.bak"), "w", encoding="utf-8") as fh:
    fh.write('{"name": "Alt Q", "items": []}\n')
with open(os.path.join(LKS_ROOT, "actions", "Ghost.py"), "w", encoding="utf-8") as fh:
    fh.write("# demo\n")
LANG = os.path.join(INSTALL, "data", "Languages")
os.makedirs(LANG, exist_ok=True)
with open(os.path.join(LANG, "English.xml"), "w", encoding="utf-8") as fh:
    # deliberately contains the same broken escape 3DCoat writes (&lt without ;)
    fh.write(
        "<ClassArray.TextItem>\n"
        "\t<TextItem><ID>CLEARSCENE</ID><Text>New</Text></TextItem>\n"
        "\t<TextItem><ID>OPEN_FILE</ID><Text>Open</Text></TextItem>\n"
        "\t<TextItem><ID>Resample</ID><Text>Resample</Text></TextItem>\n"
        "\t<TextItem><ID>WEIRD</ID><Text>a &lt b</Text></TextItem>\n"
        "</ClassArray.TextItem>\n"
    )

FAKE = install_fake_coat(DOCS, COAT_SIDE, install_root=INSTALL)

from coatmenu.core import catalog  # noqa: E402
from coatmenu.core.hotkeys import code_to_vk, find_trigger_vk, read_bindings  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== catalog ==")
check(catalog.hotkeys_path() == HOTKEYS, "hotkeys path resolves under the fake Documents folder")
commands = catalog.read_hotkey_commands()
by_id = {c.cid: c for c in commands}
check(len(commands) == 5, f"parsed all 5 hotkey ids ({len(commands)})")
check(by_id["REDO"].room == "Voxels" and by_id["VIEW_WIREFRAME"].room == "",
      "room is carried through (empty = global)")

custom = catalog.read_custom_menu_commands()
labels = {c.label: c for c in custom}
check(len(custom) == 2, f"found 2 .command entries ({len(custom)})")
check(labels["Resample"].cid == "Resample", "striped the $ from the command id")
check(labels["Shaded"].room == "VoxelsCustom/Shading", "section path preserved")

scripts = catalog.read_script_commands()
check(len(scripts) == 2, f"listed 2 scripts ({[s.label for s in scripts]})")

print("== code_to_vk ==")
check(code_to_vk("Z") == ord("Z"), "letter")
check(code_to_vk("F4") == 0x73, "function key")
check(code_to_vk("ENTER") == 0x0D, "named key")
check(code_to_vk("NUM5") == 0x65, "numpad digit")
check(code_to_vk("key_00") == 0, "unbound placeholder")
check(code_to_vk("key_6E") == 0x6E, "hex scan code")

print("== bindings ==")
bindings = read_bindings()
check(len(bindings) == 5, f"all bindings parsed ({len(bindings)})")
check(any(b["id"] == "UNDO" and b["ctrl"] for b in bindings), "modifier flags parsed")

print("== find_trigger_vk ==")
check(find_trigger_vk(["CoatMenu_Show"]) == ord("Q"), "finds the key bound to our menu id")

from coatmenu.ui import popup  # noqa: E402

popup.is_key_down = lambda _vk: False
check(find_trigger_vk(["Nope", "execute:C:\\t\\actions\\CoatMenu_Show.py"]) == 0,
      "execute: entry is bound to key_00 -> no trigger key")

with open(HOTKEYS, "w", encoding="utf-8") as fh:
    fh.write("""<AppOptions><HotKeys>
\t<OneHotKey><ID>CoatMenu_Show</ID><Room></Room><Code>Q</Code></OneHotKey>
\t<OneHotKey><ID>execute:C:/t/actions/CoatMenu_Show.py</ID><Room></Room><Code>W</Code></OneHotKey>
</HotKeys></AppOptions>
""")
popup.is_key_down = lambda vk: vk == ord("W")
check(find_trigger_vk(["CoatMenu_Show", "execute:C:\\t\\actions\\CoatMenu_Show.py"]) == ord("W"),
      "prefers the candidate that is currently held")

print("== 3DCoat's own menu definitions (authoritative, cannot be corrupted) ==")
menu = catalog.read_menu_commands()
by_menu_id = {e.cid: e for e in menu}
check(len(menu) == 5, f"menu_item ids extracted ({sorted(by_menu_id)})")
check(all(e.cid != "COMMENTED_OUT" for e in menu), "commented-out calls ignored")
check(any(e.hint == "MainMenu/File" for e in menu), "group carries the source file")
check(by_menu_id["CLEARSCENE"].label == "New",
      "the trailing comment is 3DCoat's own name for the entry")
check(by_menu_id["TRANSFORM_TRANSLATE_X"].label == "Move along the X-axis",
      "so commands read like the menu instead of like their id")
check(by_menu_id["BaseVoxBrush"].label == "BaseVoxBrush",
      "an entry without a comment keeps its id")
check(catalog.install_root() == INSTALL, "install root taken from coat.io.installPath()")

print("== labels are cleaned of 3DCoat's UI markers ==")
check(catalog.clean_label("{CY}Import for Sculpt{C}") == "Import for Sculpt",
      "colour markers come out")
check(catalog.clean_label("{maticon bool_intersection} Live Intersection") == "Live Intersection",
      "and so do icon markers")
check(catalog.clean_label("Paint Mesh ( Baked )") == "Paint Mesh (Baked)",
      "including the spaces a marker leaves behind")

print("== readable names from English.xml ==")
names = catalog.read_translations()
check(names.get("CLEARSCENE") == "New", f"id -> name ({names.get('CLEARSCENE')})")
check(len(names) == 4, f"parsed despite broken escapes ({len(names)})")

print("== combined command list ==")
combined = catalog.read_all_commands(names)
by_id = {e.cid: e for e in combined}
check(by_id["CLEARSCENE"].label == "New", "entries carry readable names")
check(by_id["Resample"].room == "VoxelsCustom", "custom-menu entries merged in")
check(len(combined) >= 7, f"union of menu + hotkeys + custom menu ({len(combined)})")

print("== 3DCoat's own tool panel (tools_item) ==")
panel = catalog.read_toolpanel_commands()
by_id = {e.cid: e for e in panel}
check(len(panel) == 4, f"panel tools extracted ({sorted(by_id)})")
check(by_id["[extension]SCULP_SCLAY"].label == "Clay",
      "the trailing comment is 3DCoat's readable name")
check(by_id["[extension]SCULP_SCLAY"].hint == "Clay/Draw", "the panel section is carried")
check("[extension]COMMENTED_TOOL" not in by_id, "a commented-out tools_item is not a tool")
check(catalog.tool_id_name("{FLT}[extension]SCULP_PLANE") == "SCULP_PLANE",
      "modifier groups and the family tag strip off")
check(catalog.tool_id_name("[extension]BendVolume") == "BendVolume", "and off a plain id")

print("== my tool presets (CustomTools/*.txt) ==")
mine = catalog.read_my_tools()
by_name = {catalog.tool_id_name(e.cid): e for e in mine}
check(len(mine) == 4, f"every preset becomes a row ({sorted(by_name)})")
check(by_name["SCULP_SCLAY"].cmd_string == "$[extension]SCULP_SCLAY",
      "a row runs the tool id itself, not the file name")
check(by_name["BendVolume"].label == "Array/Bend Volume",
      "the readable name comes from 3DCoat's panel definition")
check(by_name["SCULP_SCLAY"].hint == "Clay/Draw", "and so does the section")
check(by_name["SomePersonalTool"].hint == "Other",
      "a preset 3DCoat's panels do not list still gets a row")

from coatmenu.core import presets  # noqa: E402

tools_preset = presets.tools_list()
check([i.label for i in tools_preset.items] == ["Clay/Draw  (1)", "Layers  (2)", "Other  (1)"],
      f"the Tools list groups them like 3DCoat's panel "
      f"({[i.label for i in tools_preset.items]})")
check(any(child.cid == "$[extension]BendVolume" for child in tools_preset.items[1].children),
      "rows inside a group are runnable tool ids")

print("== saved tool presets (Presets panel) ==")
saved = catalog.read_presets()
check([e.label for e in saved] == ["HS_Extrude", "HS_分层Split"],
      f"order.txt order kept, <Name> used instead of the file name "
      f"({[e.label for e in saved]})")
check(saved[1].cid == "HS_分层Split", "the real (non-ASCII) name is the payload")
check(saved[0].source == "preset", "and it is tagged as a preset source")

print("== the Common list (everyday commands, 3DCoat's own grouping) ==")
groups = presets.common_groups()
check([name for name, _ in groups] == ["Edit"],
      f"only the menus we ask for ({[name for name, _ in groups]})")
check([i.label for i in groups[0][1]] == ["Move along the X-axis", "Undo"],
      f"named like the catalog ({[i.label for i in groups[0][1]]})")
common = presets.common_list()
check([i.label for i in common.items] == ["Edit  (2)"], "and it becomes one submenu per menu")
check(common.preset == "common/1", "with its own marker")

print("== LKS radial menus (read-only import) ==")
from coatmenu.core import lks  # noqa: E402

menus = lks.read_menus()
by_name = {m.name: m for m in menus}
check([m.name for m in menus] == ["Booleans", "Shift S"],
      f"menu names with the LKS_Radial_ prefix dropped ({[m.name for m in menus]})")
booleans = by_name["Booleans"].items
check([r.label for r in booleans] == ["Apply", "New", "Ghost"],
      f"placeholders and module.function rows dropped ({[r.label for r in booleans]})")
check(booleans[0].kind == "command" and booleans[0].cid == "$LKS_Apply",
      "$ commands stay commands")
check(booleans[1].children[0].cid == "$LKS_Union", "nested list rows come through")
check(booleans[2].kind == "script" and booleans[2].path.endswith("Ghost.py"),
      f"actions/X.py becomes a runnable script row ({booleans[2].path})")
check(by_name["Shift S"].items[0].label == "Reset Axis",
      "the user's own LKS menu is included")

lks_preset = presets.lks_list()
check([i.label for i in lks_preset.items] == ["Booleans  (3)", "Shift S  (1)"],
      f"the LKS list makes one submenu per menu ({[i.label for i in lks_preset.items]})")
check(lks_preset.preset == "lks/1", "with a marker of its own")

print("== a hotkeys file broken by 3DCoat still parses ==")
# 3DCoat writes '&lt'/'&gt' without the semicolon; a strict XML parser rejects the
# whole document, which is what used to leave the command list nearly empty.
with open(HOTKEYS, "w", encoding="utf-8") as fh:
    fh.write('<AppOptions><HotKeys>\n'
             '\t<OneHotKey><ID>UNDO</ID><Room>Voxels</Room><Code>Z</Code><Ctrl>true</Ctrl></OneHotKey>\n'
             '\t<OneHotKey><ID>DEC_SPEC_DEGREE</ID><Room>Voxels</Room><Code>&lt</Code></OneHotKey>\n'
             '\t<OneHotKey><ID>INC_SPEC_DEGREE</ID><Room>Voxels</Room><Code>&gt</Code></OneHotKey>\n'
             '</HotKeys></AppOptions>\n')
ids = catalog.read_hotkey_commands()
check(len(ids) == 3, f"every id recovered from the broken file ({len(ids)})")
broken_bindings = read_bindings()
check(len(broken_bindings) == 3, f"bindings recover too ({len(broken_bindings)})")
check(any(b["code"] == "&lt" for b in broken_bindings),
      "the corrupt value stays visible instead of killing the file")

print()
if failures:
    print(f"CATALOG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CATALOG REGRESSION PASSED")
sys.exit(0)
