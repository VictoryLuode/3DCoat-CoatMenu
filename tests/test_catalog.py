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
# The VoxTree right-click menu - one of the sources the catalog reads, and
# the place a build may differ from the one that preset was written on.
with open(os.path.join(CMAKE, "voxTreeRmb.py"), "w", encoding="utf-8") as fh:
    fh.write(
        'import coat\n'
        'coat.menu_item("Decimate")   # Decimate\n'
        'coat.menu_item("LiveUnion")  # Live union\n'
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
check(len(menu) == 7, f"menu_item ids extracted ({sorted(by_menu_id)})")
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

# A build whose id table we can read, but which knows none of these commands: say
# so in the list rather than offer rows that cannot resolve.
real_ids = catalog.known_command_ids
real_reader = catalog.read_menu_commands
catalog.read_menu_commands = lambda *a, **k: []
catalog.known_command_ids = lambda: {"SOMETHING_ELSE"}
try:
    empty = presets.shade_list()
finally:
    catalog.read_menu_commands = real_reader
    catalog.known_command_ids = real_ids
check(len(empty.items) == 1 and empty.items[0].kind == "header",
      f"with nothing to show it says so ({empty.items[0].label})")

# ...but with no id table at all there is nothing to check against, so the rows
# stay: dropping everything would be a guess, and a wrong one on a build whose
# English.xml merely moved.
catalog.known_command_ids = lambda: set()
try:
    unverifiable = presets.shade_list()
finally:
    catalog.known_command_ids = real_ids
check(len(unverifiable.items) == len(presets.SHADE_MENU_ROWS),
      f"without an id table the rows are kept, not dropped "
      f"({len(unverifiable.items)} groups)")

print()
if failures:
    print(f"CATALOG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CATALOG REGRESSION PASSED")
sys.exit(0)
