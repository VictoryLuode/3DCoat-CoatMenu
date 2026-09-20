"""
.3dcpack test - unpack the real package the way 3DCoat does, and see it come up.

The package ships the extension only: no ``startup.txt`` (shipping that file would
replace 3DCoat's auto-launch list and wipe every other add-on out of it), and no
generated launchers or menu XML (they depend on the user's config and carry
absolute paths). Everything they need has to appear on its own at first start -
that is what this test checks, because nobody runs an installer for a package.

Run:  QT_QPA_PLATFORM=offscreen python tests/test_3dcpack.py
"""
from __future__ import annotations

import os
import runpy
import subprocess
import sys
import tempfile
import types
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAKE = os.path.join(ROOT, "tools", "make_release.py")
sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 3DCoat unpacks the entries straight over ``Documents/3DCoat`` - that is the root
# the paths inside a .3dcpack are relative to.
DOCS = tempfile.mkdtemp(prefix="coatmenu-pack-")
INSTALL_ROOT = os.path.join(DOCS, "3DCoat")
USER_PREFS = os.path.join(INSTALL_ROOT, "UserPrefs")
os.makedirs(USER_PREFS, exist_ok=True)
LOG = os.path.join(tempfile.mkdtemp(prefix="coatmenu-packlog-"), "CoatMenu.log")
os.environ["COATMENU_LOG_PATH"] = LOG

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


print("== build the package ===")
built = subprocess.run([sys.executable, MAKE], capture_output=True, text=True)
check(built.returncode == 0, f"make_release.py exited 0 ({built.stderr.strip()[:200]})")
packs = [n for n in os.listdir(os.path.join(ROOT, "dist")) if n.endswith(".3dcpack")]
check(bool(packs), f"a .3dcpack came out ({packs})")
pack = os.path.join(ROOT, "dist", sorted(packs)[-1])

# 3DCoat unpacks the entries straight over UserPrefs.
STARTUP = os.path.join(USER_PREFS, "Scripts", "cExtensions", "startup.txt")
os.makedirs(os.path.dirname(STARTUP), exist_ok=True)
existing = "SomeOtherAddon\nLKS\n"
with open(STARTUP, "w", encoding="utf-8") as fh:
    fh.write(existing)

print("== unpack it like 3DCoat does ==")
with zipfile.ZipFile(pack) as zf:
    names = zf.namelist()
    check(not any("startup.txt" in n for n in names),
          "the package carries no startup.txt (it would replace the user's)")
    check(not any("ExtraMenuItems" in n for n in names),
          "and no menu XML (absolute paths, per-user)")
    zf.extractall(INSTALL_ROOT)

EXT = os.path.join(USER_PREFS, "Scripts", "cExtensions", "CoatMenu")
check(os.path.isdir(EXT), "the extension landed under Scripts/cExtensions/CoatMenu")

print("== first start: the extension has to build the rest itself ==")
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
for name in ("ui", "core"):  # another add-on got there first
    stub = types.ModuleType(name)
    stub.__path__ = []
    sys.modules.setdefault(name, stub)


def read_startup() -> str:
    if not os.path.exists(STARTUP):
        return ""
    with open(STARTUP, encoding="utf-8") as fh:
        return fh.read()


if EXT not in sys.path:
    sys.path.insert(0, EXT)

module = runpy.run_path(os.path.join(EXT, "CoatMenu.py"))
extension = module.get("_extension")
check(extension is not None, "the package's entry module loads")

try:
    extension.onStartup()
    startup_error = None
except Exception as exc:  # noqa: BLE001
    startup_error = exc
check(startup_error is None, f"onStartup ran ({startup_error})")

check(os.path.isfile(os.path.join(EXT, "data", "menus.json")),
      "a config was written on first start")
check(os.path.isfile(os.path.join(EXT, "actions", "menus", "CoatMenu_Sculpt.py")),
      "the per-menu launcher was generated")
check(os.path.isfile(os.path.join(USER_PREFS, "Scripts", "ExtraMenuItems", "CoatMenu.xml")),
      "the menu XML was generated")
check(FAKE.translations.get("CoatMenu_Show") == "Show CoatMenu",
      "the menu label was registered with 3DCoat")

check(read_startup() == existing,
      f"startup.txt is untouched ({read_startup()!r}) - the user ticks Auto-Launch "
      f"in Windows > Panels > Extensions instead")

print("== clicking the menu item works on an installed-by-package copy ==")
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])
try:
    runpy.run_path(os.path.join(EXT, "actions", "CoatMenu_Show.py"))
    show_error = None
except Exception as exc:  # noqa: BLE001
    show_error = exc
check(show_error is None, f"Show CoatMenu ran ({show_error})")

from coatmenu.ui import popup  # noqa: E402

manager = popup.get_manager()
check(manager.is_visible(), "the overlay opened")
popup.hide_menu()

with open(LOG, encoding="utf-8") as fh:
    log_text = fh.read()
check("IMPORT FAILED" not in log_text and "RUN FAILED" not in log_text,
      "no import/run failures logged")

print()
if failures:
    print(f"3DCPACK FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("3DCPACK REGRESSION PASSED")
sys.exit(0)
