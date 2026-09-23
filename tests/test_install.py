"""
Installer tests - installs into a throwaway Documents tree and checks that we
only ever touch our own files.

Run:  python tests/test_install.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INSTALL = os.path.join(ROOT, "install", "install.py")

DOCS = tempfile.mkdtemp(prefix="coatmenu-install-")
USERPREF = os.path.join(DOCS, "3DCoat", "UserPrefs")
os.makedirs(os.path.join(USERPREF, "Scripts", "cExtensions"), exist_ok=True)
STARTUP = os.path.join(USERPREF, "Scripts", "cExtensions", "startup.txt")
with open(STARTUP, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("debugger\nQT\nLKS\n")

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, INSTALL, "--documents", DOCS, *args],
                          capture_output=True, text=True)


ext = os.path.join(USERPREF, "Scripts", "cExtensions", "CoatMenu")
xml = os.path.join(USERPREF, "Scripts", "ExtraMenuItems", "CoatMenu.xml")

print("== install ==")
result = run()
check(result.returncode == 0, f"installer exits 0 ({result.returncode}) {result.stderr.strip()}")
check(os.path.isfile(os.path.join(ext, "CoatMenu.py")), "extension entry point copied")
check(os.path.isfile(os.path.join(ext, "actions", "CoatMenu_Show.py")), "action script copied")
check(os.path.isfile(os.path.join(ext, "coatmenu", "ui", "popup.py")),
      "ui package copied (under the namespaced package)")
check(not os.path.isdir(os.path.join(ext, "tests")), "tests are not shipped")
check(not os.path.isdir(os.path.join(ext, "__pycache__")), "no __pycache__ shipped")

check(os.path.isfile(xml), "ExtraMenuItems xml written")
with open(xml, encoding="utf-8") as fh:
    xml_text = fh.read()
check("<MenuItem>CoatMenu_Show</MenuItem>" in xml_text, "menu id registered")
abs_script = os.path.join(ext, "actions", "CoatMenu_Show.py").replace("\\", "/")
check(f"<Command>script:{abs_script}</Command>" in xml_text, "absolute script path in xml (forward slashes)")
check("<MenuPath>Scripts</MenuPath>" in xml_text, "menu item lives under Scripts")

with open(STARTUP, encoding="utf-8") as fh:
    startup_text = fh.read()
check(startup_text.splitlines() == ["debugger", "QT", "LKS", "CoatMenu"],
      f"startup.txt has exactly our added line: {startup_text.splitlines()}")
check(os.path.isfile(STARTUP + ".bak-coatmenu-" + os.listdir(os.path.dirname(STARTUP))[0].split("-")[-1])
      or any(name.startswith("startup.txt.bak-coatmenu-") for name in os.listdir(os.path.dirname(STARTUP))),
      "startup.txt was backed up before editing")

print("== reinstall is idempotent ==")
before = open(STARTUP, encoding="utf-8").read()
result = run()
check(result.returncode == 0, "second install exits 0")
after = open(STARTUP, encoding="utf-8").read()
check(before == after, "startup.txt is not duplicated on reinstall")

print("== stale modules from an older version are pruned ==")
stale = os.path.join(ext, "coatmenu", "core", "menu_data.py")
with open(stale, "w", encoding="utf-8") as fh:
    fh.write("# left over from an older version\n")
# ...and an old top-level package that 3DCoat already littered debug stubs into
old_pkg = os.path.join(ext, "ui")
os.makedirs(old_pkg, exist_ok=True)
with open(os.path.join(old_pkg, "legacy.py"), "w", encoding="utf-8") as fh:
    fh.write("# old layout\n")
with open(os.path.join(old_pkg, ".env"), "w", encoding="utf-8") as fh:
    fh.write("3DCoat generated debug stub\n")
result = run()
check(not os.path.exists(stale), "stale module removed by the next install")
check(not os.path.isdir(old_pkg), "old top-level package folder removed, stubs and all")
check(os.path.isfile(os.path.join(ext, "data", "menus.json")),
      "menus.json materialised on first install")
check(os.path.isdir(os.path.join(ext, "actions", "menus")), "launcher folder created")
check(os.path.isdir(os.path.join(ext, "coatmenu", "core")), "namespaced package intact")

print("== an update deletes nothing it did not write ==")
mine_dir = os.path.join(ext, "my_scripts")
os.makedirs(mine_dir, exist_ok=True)
for path, text in ((os.path.join(mine_dir, "mine.py"), "# a script of the user's\n"),
                   (os.path.join(ext, "Loose.py"), "# dropped in by hand\n"),
                   (os.path.join(ext, "notes.txt"), "notes\n")):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)

# ...next to a stale `ported/` tree, which is what the version before this one put
# there: its own .py files plus icons and 3DCoat's .env stubs, none of which
# pruning alone would have taken away.
ported_dir = os.path.join(ext, "ported")
os.makedirs(os.path.join(ported_dir, "ops"), exist_ok=True)
os.makedirs(os.path.join(ported_dir, "ui", "data"), exist_ok=True)
for path, text in ((os.path.join(ported_dir, "ops", "Decimate.py"), "# old copy\n"),
                   (os.path.join(ported_dir, "ops", ".env"), "3DCoat debug stub\n"),
                   (os.path.join(ported_dir, "ui", "data", "decimate.svg"), "<svg/>\n")):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)

result = run()
check(result.returncode == 0, "install exits 0")
check(os.path.isfile(os.path.join(mine_dir, "mine.py")),
      "a folder of your own inside the extension is left alone")
check(os.path.isfile(os.path.join(ext, "Loose.py")), "a loose .py of yours is left alone")
check(os.path.isfile(os.path.join(ext, "notes.txt")), "a file of your own is left alone")
check(not os.path.isdir(ported_dir),
      "while the retired ported/ tree is removed whole - stubs and icons included")
check(not os.path.exists(stale), "and a stale module of ours is still pruned")

print("== an update leaves your own menus alone ==")
# The rule this whole section exists for: 3DCoat's menus are the user's. An
# install may add a list that is missing; it must never rename, reorder, edit or
# drop one he built.
config_path = os.path.join(ext, "data", "menus.json")
mine = {
    "version": 1,
    "menus": [
        {"name": "My Stuff", "items": [{"id": "Resample", "label": "Resample"}],
         "mode": "pie"},
        # ...and a hand-built list that happens to shadow a built-in name.
        {"name": "Prims", "items": [{"id": "Mine", "label": "Mine"}]},
    ],
}
with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(mine, fh, indent=2)

def row_ids(rows) -> list:
    """Command ids of a saved menu's rows (a row may be a bare string or an object)."""
    return [r if isinstance(r, str) else r.get("id") for r in rows]


result = run()
check(result.returncode == 0, f"install exits 0 with a hand-written config ({result.stderr.strip()})")
with open(config_path, encoding="utf-8") as fh:
    after = json.load(fh)
names = [m["name"] for m in after["menus"]]
check("My Stuff" in names, "a hand-built menu survives an update")
_mine = after["menus"][names.index("My Stuff")]
check(_mine.get("mode") == "pie" and _mine["name"] == "My Stuff",
      "with his name and his pie mode untouched")
check(row_ids(_mine["items"]) == ["Resample"], "and his rows, in his order")
check(names.count("Prims") == 1 and row_ids(after["menus"][names.index("Prims")]["items"]) == ["Mine"],
      "a hand-built 'Prims' is never mistaken for the built-in preset")
check(any(m.get("preset") for m in after["menus"]),
      "while a preset that is actually missing still installs")

print("== a menus file we cannot read is never written over ==")
bad_text = '{"version": 1, "menus": [ {oops\n'
with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(bad_text)
result = run()
check(result.returncode == 0, "install still exits 0")
check(result.stdout.count("unreadable") >= 1, "and says so out loud")
with open(config_path, encoding="utf-8") as fh:
    check(fh.read() == bad_text, "the file is byte-for-byte what it was")
check(any(n.startswith("menus.json.unreadable-") for n in os.listdir(os.path.dirname(config_path))),
      "with a dated copy kept beside it")

print("== uninstall ==")
result = run("--uninstall")
check(result.returncode == 0, "uninstall exits 0")
check(not os.path.isdir(ext), "extension folder removed")
check(not os.path.isfile(xml), "menu xml removed")
with open(STARTUP, encoding="utf-8") as fh:
    lines = fh.read().splitlines()
check(lines == ["debugger", "QT", "LKS"], f"other extensions untouched: {lines}")

print("== uninstall touches nothing but its own files ==")
# A second, controlled tree: another extension's item file and folder next to ours,
# and the user's own edited lists - the whole round trip in one place.
DOCS2 = tempfile.mkdtemp(prefix="coatmenu-roundtrip-")
SCRIPTS2 = os.path.join(DOCS2, "3DCoat", "UserPrefs", "Scripts")
STARTUP2 = os.path.join(SCRIPTS2, "cExtensions", "startup.txt")
ITEMS2 = os.path.join(SCRIPTS2, "ExtraMenuItems")
os.makedirs(os.path.join(SCRIPTS2, "cExtensions", "OtherExtension"), exist_ok=True)
os.makedirs(ITEMS2, exist_ok=True)
with open(STARTUP2, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("debugger\nQT\nLKS\n")
FOREIGN_XML = os.path.join(ITEMS2, "SomeOtherTool.xml")
with open(FOREIGN_XML, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("<Root><MenuItem>Other</MenuItem></Root>\n")
FOREIGN_PY = os.path.join(SCRIPTS2, "cExtensions", "OtherExtension", "keep.py")
with open(FOREIGN_PY, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("print('mine')\n")


def run2(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, INSTALL, "--documents", DOCS2, *args],
                          capture_output=True, text=True)


ext2 = os.path.join(SCRIPTS2, "cExtensions", "CoatMenu")
config2 = os.path.join(ext2, "data", "menus.json")
result = run2()
check(result.returncode == 0, f"install into a fresh tree exits 0 ({result.stderr.strip()})")

# The user edits their lists: one menu kept under a new name, the others dropped.
with open(config2, encoding="utf-8") as fh:
    starter = json.load(fh)
kept_name = starter["menus"][0]["name"] + " (mine)"
edited = {"version": starter.get("version", 1),
          "menus": [{"name": kept_name, "items": starter["menus"][0]["items"]}]}
with open(config2, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(edited, fh, indent=2)
edited_text = open(config2, encoding="utf-8").read()

# 3DCoat persists one item file per menu it registered for us.
own_item = os.path.join(ITEMS2, "CoatMenu_RoundTrip.xml")
own_script = os.path.join(ext2, "actions", "menus", "CoatMenu_RoundTrip.py").replace("\\", "/")
with open(own_item, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(f"<Root><MenuItem>CoatMenu_RoundTrip</MenuItem>"
             f"<Command>script:{own_script}</Command></Root>\n")

result = run2("--uninstall")
check(result.returncode == 0, f"uninstall exits 0 ({result.stderr.strip()})")
check(not os.path.isdir(ext2), "the extension folder is removed")
check(not os.path.isfile(os.path.join(ITEMS2, "CoatMenu.xml")), "our menu xml is removed")
check(not os.path.isfile(own_item), "and the item file 3DCoat wrote for one of our menus")
check(open(FOREIGN_XML, encoding="utf-8").read() == "<Root><MenuItem>Other</MenuItem></Root>\n",
      "another extension's item file is untouched")
check(os.path.isfile(FOREIGN_PY), "and another extension's folder")
with open(STARTUP2, encoding="utf-8") as fh:
    check(fh.read().splitlines() == ["debugger", "QT", "LKS"],
          "startup.txt keeps their lines and drops ours")
backup2 = os.path.join(DOCS2, "3DCoat", "CoatMenu-menus-backup.json")
check(os.path.isfile(backup2) and open(backup2, encoding="utf-8").read() == edited_text,
      "and the user's edited lists were kept in a backup")

print("== installing again brings those lists back ==")
result = run2()
check(result.returncode == 0, f"reinstall exits 0 ({result.stderr.strip()})")
with open(config2, encoding="utf-8") as fh:
    back = json.load(fh)
names = [menu["name"] for menu in back["menus"]]
check(kept_name in names, f"the user's own menu is back ({names})")
check("restored" in result.stdout, f"and the installer says where from ({result.stdout.strip()})")
check(os.path.isfile(os.path.join(ITEMS2, "CoatMenu.xml")), "with the menu files rebuilt")
check(len(names) > 1,
      f"and the built-in lists that were missing are added back, never touched ({names})")
check(os.path.isfile(backup2), "the backup is left beside it as a safety copy")

print()
if failures:
    print(f"INSTALL FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("INSTALL REGRESSION PASSED")
sys.exit(0)
