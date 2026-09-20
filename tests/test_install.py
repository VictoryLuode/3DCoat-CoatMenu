"""
Installer tests - installs into a throwaway Documents tree and checks that we
only ever touch our own files.

Run:  python tests/test_install.py
"""
from __future__ import annotations

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

print("== uninstall ==")
result = run("--uninstall")
check(result.returncode == 0, "uninstall exits 0")
check(not os.path.isdir(ext), "extension folder removed")
check(not os.path.isfile(xml), "menu xml removed")
with open(STARTUP, encoding="utf-8") as fh:
    lines = fh.read().splitlines()
check(lines == ["debugger", "QT", "LKS"], f"other extensions untouched: {lines}")

print()
if failures:
    print(f"INSTALL FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("INSTALL REGRESSION PASSED")
sys.exit(0)
