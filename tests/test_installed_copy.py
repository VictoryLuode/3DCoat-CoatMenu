"""
Installed-copy test - the closest thing to "click the menu item" without 3DCoat.

Installs into a throwaway Documents tree, then imports the *installed* entry
scripts by path with:

* a fake ``coat`` module (there is no 3DCoat here),
* stubs already occupying the generic top-level names ``ui`` and ``core``,
  standing in for whatever other cExtension got there first,
* Qt in offscreen mode.

This is the check that would have caught the first release's silent failure: it
went looking for ``ui.popup`` and found another add-on's ``ui`` package instead.

Run:  QT_QPA_PLATFORM=offscreen python tests/test_installed_copy.py
"""
from __future__ import annotations

import os
import runpy
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
INSTALL = os.path.join(ROOT, "install", "install.py")
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DOCS = tempfile.mkdtemp(prefix="coatmenu-installed-")
LOG = os.path.join(tempfile.mkdtemp(prefix="coatmenu-log-"), "CoatMenu.log")
os.environ["COATMENU_LOG_PATH"] = LOG

# One CustomMenu entry so the starter config has something in it.
MENU_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "CustomMenu", "VoxelsCustom")
os.makedirs(MENU_DIR, exist_ok=True)
with open(os.path.join(MENU_DIR, "Resample.command"), "w", encoding="utf-8") as fh:
    fh.write("Resample\n$Resample\nhint\n")

result = subprocess.run([sys.executable, INSTALL, "--documents", DOCS],
                        capture_output=True, text=True)
EXT = os.path.join(DOCS, "3DCoat", "UserPrefs", "Scripts", "cExtensions", "CoatMenu")

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== install into a throwaway tree ==")
check(result.returncode == 0, f"installer exited 0 ({result.stderr.strip()[:120]})")
check(os.path.isfile(os.path.join(EXT, "actions", "CoatMenu_Show.py")), "entries installed")

# --- the environment 3DCoat would provide ----------------------------------
from fake_coat import install_fake_coat  # noqa: E402

FAKE = install_fake_coat(DOCS, EXT)

cPy = types.ModuleType("cPy")
cCore = types.ModuleType("cPy.cCore")


class Base:
    def __init__(self):
        pass


cCore.cExtension = Base
cPy.cCore = cCore
sys.modules["cPy"] = cPy
sys.modules["cPy.cCore"] = cCore

# Another add-on got there first - the exact shape of the original bug.
for name in ("ui", "core"):
    stub = types.ModuleType(name)
    stub.__path__ = []
    sys.modules.setdefault(name, stub)

# 3DCoat puts the extension folder on sys.path before running an action script.
if EXT not in sys.path:
    sys.path.insert(0, EXT)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

print("== the extension module imports ==")
module = runpy.run_path(os.path.join(EXT, "CoatMenu.py"))
check("CoatMenuExtension" in module, "extension class defined in the installed copy")
check(isinstance(module.get("_extension"), Base), "extension instance registered")

print("== clicking 'Show CoatMenu' runs the installed entry script ==")
try:
    runpy.run_path(os.path.join(EXT, "actions", "CoatMenu_Show.py"))
    show_error = None
except Exception as exc:  # noqa: BLE001
    show_error = exc
check(show_error is None, f"Show entry ran without raising ({show_error})")

from coatmenu.ui import popup  # noqa: E402

manager = popup.get_manager()
check(manager.is_visible(), "the overlay actually opened")
check(manager.popup is not None and len(manager.popup._rows) >= 2,
      f"overlay has rows ({manager.popup and len(manager.popup._rows)})")
popup.hide_menu()

print("== the overlay's rows come from the installed config ==")
launcher = os.path.join(EXT, "actions", "lists", "CoatMenu_List_Sculpt.py")
check(os.path.isfile(launcher), "per-list launcher generated")
try:
    runpy.run_path(launcher)
    list_error = None
except Exception as exc:  # noqa: BLE001
    list_error = exc
check(list_error is None, f"list launcher ran without raising ({list_error})")
check(manager.is_visible(), "the list overlay opened")
popup.hide_menu()

print("== clicking 'Edit lists' opens the editor ==")
try:
    runpy.run_path(os.path.join(EXT, "actions", "CoatMenu_Editor.py"))
    editor_error = None
except Exception as exc:  # noqa: BLE001
    editor_error = exc
check(editor_error is None, f"editor entry ran without raising ({editor_error})")
from coatmenu.ui.editor import get_editor  # noqa: E402

check(get_editor().isVisible(), "editor panel is visible")
get_editor().close_editor()

print("== a second click runs again (3DCoat caches imports) ==")
# 3DCoat runs a menu script as exec("import <module name>"), so the module stays
# in sys.modules unless it removes itself - the bug behind "it worked once".
import importlib  # noqa: E402

actions_dir = os.path.join(EXT, "actions")
if actions_dir not in sys.path:
    sys.path.insert(0, actions_dir)


def count_in_log(needle: str) -> int:
    with open(LOG, encoding="utf-8") as fh:
        return fh.read().count(needle)


sys.modules.pop("CoatMenu_Show", None)
before = count_in_log("menu item: show")
importlib.import_module("CoatMenu_Show")
app.processEvents()
check("CoatMenu_Show" not in sys.modules,
      "the entry un-registers itself, so the import cache cannot swallow the next click")
importlib.import_module("CoatMenu_Show")
app.processEvents()
after = count_in_log("menu item: show")
check(after == before + 2, f"two consecutive clicks both ran ({before} -> {after})")
popup.hide_menu()

print("== the log tells the story ==")
with open(LOG, encoding="utf-8") as fh:
    log_text = fh.read()
check("menu item: show" in log_text, "click logged")
check("menu item: list Sculpt" in log_text, "list click logged")
check("menu item: editor" in log_text, "editor click logged")
check("IMPORT FAILED" not in log_text and "RUN FAILED" not in log_text,
      "no import/run failures logged")

print()
if failures:
    print(f"INSTALLED FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("INSTALLED REGRESSION PASSED")
sys.exit(0)
