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

FAKE = install_fake_coat(DOCS, COAT_SIDE)

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

print()
if failures:
    print(f"CATALOG FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("CATALOG REGRESSION PASSED")
sys.exit(0)
