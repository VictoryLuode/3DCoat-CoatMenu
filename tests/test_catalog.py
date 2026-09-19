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
with open(os.path.join(CMAKE, "sculptTools.py"), "w", encoding="utf-8") as fh:
    fh.write('import coat\ncoat.menu_item("BaseVoxBrush")\ncoat.menu_item("CLEARSCENE")\n')
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
check(len(menu) == 3, f"menu_item ids extracted ({sorted(e.cid for e in menu)})")
check(all(e.cid != "COMMENTED_OUT" for e in menu), "commented-out calls ignored")
check(any(e.hint == "MainMenu/File" for e in menu), "group carries the source file")
check(catalog.install_root() == INSTALL, "install root taken from coat.io.installPath()")

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
