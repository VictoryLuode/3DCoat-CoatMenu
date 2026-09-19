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


print("== import registers the extension ==")
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

print("== room change / exit are safe with no overlay open ==")
ext.onChangeRoom()
ext.onExit()
check(True, "onChangeRoom + onExit do not raise with nothing shown")

print("== menu label is registered through the translation table ==")
from core.show import MENU_HOTKEY_ID, MENU_LABEL, apply_labels  # noqa: E402

apply_labels()
check(FAKE.translations.get(MENU_HOTKEY_ID) == MENU_LABEL,
      f"addTranslation called with {MENU_HOTKEY_ID} -> {FAKE.translations.get(MENU_HOTKEY_ID)}")

print("== entry script is unconditional (never name-guarded) ==")
with open(os.path.join(COAT_SIDE, "actions", "CoatMenu_Show.py"), encoding="utf-8") as fh:
    entry_source = fh.read()
check("if __name__" not in entry_source,
      "action entry has no __name__ guard (3DCoat imports by module name)")
check("main()\n" in entry_source, "action entry calls main() unconditionally")

print()
if failures:
    print(f"EXTENSION FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("EXTENSION REGRESSION PASSED")
sys.exit(0)
