"""
Extension lifecycle tests.

Imports ``CoatMenu.py`` exactly as 3DCoat does - by module name, with a fake
``cPy.cCore`` standing in for the host - and exercises the per-frame hooks. This
is the only way to catch the two classic 3DCoat plugin bugs without launching the
application: a guarded entry point that never runs, and a module-cache clear that
removes a module during its own import.

Run:  QT_QPA_PLATFORM=offscreen python tests/test_extension.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
sys.path.insert(0, HERE)
sys.path.insert(0, COAT_SIDE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fake_coat import install_fake_coat  # noqa: E402

DOCS = tempfile.mkdtemp(prefix="coatmenu-ext-")
os.environ["COATMENU_DATA_DIR"] = tempfile.mkdtemp(prefix="coatmenu-ext-data-")
FAKE = install_fake_coat(DOCS, COAT_SIDE)

# --- fake cPy.cCore --------------------------------------------------------
cPy = types.ModuleType("cPy")
cCore = types.ModuleType("cPy.cCore")


class FakeCExtension:
    def __init__(self):
        self.started = False


cCore.cExtension = FakeCExtension
cPy.cCore = cCore
sys.modules["cPy"] = cPy
sys.modules["cPy.cCore"] = cCore

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


# --- simulate another cExtension having claimed the generic names first ------
# Every cExtension shares one interpreter and LKS ships its own top-level 'ui'
# package. These stubs stand in for it: if CoatMenu went back to a top-level
# 'ui'/'core', the import below would fail - which is exactly the bug that made
# the first release silently do nothing when clicked.
_stub_ui = types.ModuleType("ui")
_stub_ui.__path__ = []
_stub_core = types.ModuleType("core")
_stub_core.__path__ = []
sys.modules.setdefault("ui", _stub_ui)
sys.modules.setdefault("core", _stub_core)

print("== import registers the extension ('ui'/'core' already taken) ==")
import CoatMenu  # noqa: E402  (import by module name, as 3DCoat does)
check(isinstance(CoatMenu._extension, FakeCExtension),
      "module-level instantiation registered a cExtension")
ext = CoatMenu._extension

print("== per-frame hooks ==")
ext.preprocess()
check(True, "preprocess (Qt event pump) does not raise")
ext.postprocess()
check(True, "postprocess does not raise")

print("== module cache clearing (re-runnable menu item) ==")
stale = types.ModuleType("coatmenu_stale_action")
sys.modules["coatmenu_stale_action"] = stale
sys._coatmenu_modules_to_clear = {"coatmenu_stale_action"}
ext.postprocess()
check("coatmenu_stale_action" not in sys.modules,
      "queued action module is dropped one frame later")
check(not sys._coatmenu_modules_to_clear, "the queue is emptied")

print("== onExtendMenu registers entries and their keys through 3DCoat's API ==")
from coatmenu.core import menus as menus_mod  # noqa: E402
from coatmenu.core.config import Menu as MenuModel  # noqa: E402

# Give one menu and one of its rows a key, then run the menu pass.
live = menus_mod.get_config()
if not live.menus:
    live.menus.append(MenuModel(name="Sculpt"))
live.menus[0].hotkey = {"key": "J", "ctrl": True, "shift": False, "alt": False}
if not live.menus[0].items:
    from coatmenu.core.menu_model import MenuItem as RowModel  # noqa: E402
    live.menus[0].items.append(RowModel(label="Resample", cid="Resample"))
live.menus[0].items[0].hotkey = {"key": "K", "ctrl": False, "shift": True, "alt": False}

hotkeys_mod = None
try:
    from coatmenu.core import hotkeys as hotkeys_mod  # noqa: E402
except Exception:
    pass
_real_user_defined = getattr(hotkeys_mod, "user_defined_ids", None)
if hotkeys_mod is not None:
    hotkeys_mod.user_defined_ids = lambda path=None: set()  # pretend nothing is bound

FAKE.menu_api.clear()
FAKE.hotkey_api.clear()
ext.onExtendMenu()
if hotkeys_mod is not None and _real_user_defined is not None:
    hotkeys_mod.user_defined_ids = _real_user_defined

check(len(FAKE.menu_api) >= 2,
      f"every entry goes in via coat.menu_item ({len(FAKE.menu_api)} calls)")
check(all(str(i).startswith("$execute:") for i in FAKE.menu_api),
      f"as $execute script items ({FAKE.menu_api[:1]})")
check(("J", 0, 1, 0) in FAKE.hotkey_api,
      f"the menu's key is attached right after it ({FAKE.hotkey_api})")
check(any(h[0] == "K" for h in FAKE.hotkey_api),
      "and so is the row's key")

FAKE.hotkey_api.clear()
if hotkeys_mod is not None:
    hotkeys_mod.user_defined_ids = lambda path=None: {live.menus[0].hotkey_id}
ext.onExtendMenu()
if hotkeys_mod is not None and _real_user_defined is not None:
    hotkeys_mod.user_defined_ids = _real_user_defined
check(all(h[0] != "J" for h in FAKE.hotkey_api),
      "a key the user set by hand is never proposed over")

print("== room change / exit are safe with no overlay open ==")
ext.onChangeRoom()
ext.onExit()
check(True, "onChangeRoom + onExit do not raise with nothing shown")

print("== menu label is registered through the translation table ==")
from coatmenu.core.show import MENU_HOTKEY_ID, MENU_LABEL, apply_labels  # noqa: E402

apply_labels()
check(FAKE.translations.get(MENU_HOTKEY_ID) == MENU_LABEL,
      f"addTranslation called with {MENU_HOTKEY_ID} -> {FAKE.translations.get(MENU_HOTKEY_ID)}")

print("== entry script is unconditional (never name-guarded) ==")
with open(os.path.join(COAT_SIDE, "actions", "CoatMenu_Show.py"), encoding="utf-8") as fh:
    entry_source = fh.read()
check("if __name__" not in entry_source,
      "action entry has no __name__ guard (3DCoat imports by module name)")
check("main()\n" in entry_source, "action entry calls main() unconditionally")

print("== internal packages are namespaced ==")
# Every cExtension shares one interpreter: a top-level 'core' or 'ui' package
# collides with another add-on's (LKS ships its own 'ui', and it wins because it
# imported first). This test exists because that bug broke the first release.
top_dirs = {n for n in os.listdir(COAT_SIDE)
            if os.path.isdir(os.path.join(COAT_SIDE, n)) and not n.startswith(".")}
check("core" not in top_dirs and "ui" not in top_dirs,
      f"no generic top-level package ({sorted(top_dirs)})")
check("coatmenu" in top_dirs, "code lives under the coatmenu package")

bad: list[str] = []
for dirpath, dirnames, filenames in os.walk(COAT_SIDE):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for name in filenames:
        if not name.endswith(".py"):
            continue
        path = os.path.join(dirpath, name)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for needle in ("from core import", "from core.", "from ui import", "from ui."):
            if needle in text:
                bad.append(f"{os.path.relpath(path, COAT_SIDE)}: {needle}")
check(not bad, f"no bare core/ui imports anywhere ({bad[:3]})")

print("== entry scripts survive a broken package ==")
for entry in ("CoatMenu_Show.py", "CoatMenu_Editor.py"):
    with open(os.path.join(COAT_SIDE, "actions", entry), encoding="utf-8") as fh:
        source = fh.read()
    check("_log_raw" in source and "IMPORT FAILED" in source,
          f"{entry} reports import failures to the log file itself")

print()
if failures:
    print(f"EXTENSION FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("EXTENSION REGRESSION PASSED")
sys.exit(0)
