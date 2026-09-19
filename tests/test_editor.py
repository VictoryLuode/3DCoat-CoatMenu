"""
Editor tests - offscreen, no 3DCoat.

Covers the parts that carry risk: view <-> model round trips (including nested
submenus and a simulated drag), list operations, adding from the source catalog,
and saving (config + launcher scripts + menu XML all land in temp locations).

Run:  QT_QPA_PLATFORM=offscreen python tests/test_editor.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
sys.path.insert(0, HERE)
sys.path.insert(0, COAT_SIDE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fake_coat import install_fake_coat  # noqa: E402

DOCS = tempfile.mkdtemp(prefix="coatmenu-editor-docs-")
WORK = tempfile.mkdtemp(prefix="coatmenu-editor-work-")
os.environ["COATMENU_DATA_DIR"] = os.path.join(WORK, "data")

# A couple of CustomMenu entries so the source catalog has something real.
MENU_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "CustomMenu", "VoxelsCustom")
os.makedirs(MENU_DIR, exist_ok=True)
for name, cid in (("Resample", "$Resample"), ("Smooth", "$SmoothObject")):
    with open(os.path.join(MENU_DIR, f"{name}.command"), "w", encoding="utf-8") as fh:
        fh.write(f"{name}\n{cid}\nhint\n")

FAKE = install_fake_coat(DOCS, COAT_SIDE)

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from coatmenu.core import paths  # noqa: E402

# Keep every write inside the temp tree - never the repository's own folders.
paths.extension_root = lambda: os.path.join(WORK, "ext")
paths.entry_scripts_dir = lambda: os.path.join(WORK, "ext", "actions", "lists")
os.makedirs(paths.entry_scripts_dir(), exist_ok=True)

from coatmenu.core.config import MenuConfig, MenuList  # noqa: E402
from coatmenu.core.menu_model import MenuItem  # noqa: E402
from coatmenu.ui.editor import ROLE_KIND, CoatMenuEditor  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def fresh_editor() -> CoatMenuEditor:
    config = MenuConfig(lists=[
        MenuList(name="Sculpt", items=[
            MenuItem(label="Resample", kind="command", cid="Resample"),
            MenuItem(label="Booleans", kind="submenu", children=[
                MenuItem(label="Subtract", kind="command", cid="SubtractVolume"),
            ]),
            MenuItem(label="Wireframe", kind="command", cid="VIEW_WIREFRAME"),
        ]),
        MenuList(name="Paint", items=[MenuItem(label="Fill", kind="command", cid="FillLayer")]),
    ])
    return CoatMenuEditor(config=config)


print("== opens as a frameless panel ==")
editor = fresh_editor()
editor.show_editor()
app.processEvents()
check(editor.isVisible(), "editor is visible")
check(bool(editor.windowFlags() & Qt.FramelessWindowHint), "frameless (not a system window)")
check(editor._tree.topLevelItemCount() == 3, f"first list rows shown ({editor._tree.topLevelItemCount()})")
check(editor._tree.topLevelItem(1).childCount() == 1, "nested submenu rendered as a child node")

print("== view -> model round trip ==")
items = editor.tree_to_items()
check([i.label for i in items] == ["Resample", "Booleans", "Wireframe"], "labels survive the trip")
check(items[1].kind == "submenu" and items[1].children[0].cid == "SubtractVolume",
      "nested submenu survives the trip")
check(items[0].cid == "Resample", "command ids survive the trip")

print("== renaming a row in place ==")
editor._tree.topLevelItem(0).setText(0, "Rebuild")
check(editor.tree_to_items()[0].label == "Rebuild", "renamed label is picked up")

print("== simulated drag reorder ==")
node = editor._tree.takeTopLevelItem(0)
editor._tree.addTopLevelItem(node)
check([i.label for i in editor.tree_to_items()] == ["Booleans", "Wireframe", "Rebuild"],
      f"order follows the tree ({[i.label for i in editor.tree_to_items()]})")

print("== list operations ==")
editor._new_name.setText("Details")
editor.add_list()
check([lst.name for lst in editor._config.lists] == ["Sculpt", "Paint", "Details"],
      "list added")
editor._new_name.setText("Details x")
editor.rename_list()
check("Details x" in [lst.name for lst in editor._config.lists], "list renamed")
editor.move_list(-1)
check([lst.name for lst in editor._config.lists][1] == "Details x", "list order changed")
editor.remove_list()
check("Details x" not in [lst.name for lst in editor._config.lists], "list removed")

print("== source catalog ==")
editor.select_list(0)
editor._source_kind.setCurrentIndex(1)  # CustomMenu entries
editor.reload_sources()
check(editor._source_list.count() == 2, f"sources loaded ({editor._source_list.count()})")
editor._search.setText("Resample")
editor.reload_sources()
check(editor._source_list.count() == 1, "filter narrows the list")
editor._source_list.setCurrentRow(0)
before = editor._tree.topLevelItemCount()
editor.add_source_item()
check(editor._tree.topLevelItemCount() == before + 1, "row appended to the list")
appended = editor.tree_to_items()[-1]
check(appended.cid in ("Resample", "$Resample"), f"appended entry carries the id ({appended.cid})")

print("== adding decoration rows ==")
rows_before = editor._tree.topLevelItemCount()
editor.add_separator()
editor.add_header()
editor.add_submenu()
check(editor._tree.topLevelItemCount() == rows_before + 3, "separator + header + submenu added")
kinds = [i.kind for i in editor.tree_to_items()][-3:]
check(kinds == ["separator", "header", "submenu"], f"kinds round-trip ({kinds})")

print("== remove a row ==")
editor._tree.setCurrentItem(editor._tree.topLevelItem(0))
n = editor._tree.topLevelItemCount()
editor.remove_row()
check(editor._tree.topLevelItemCount() == n - 1, "selected row removed")

print("== save writes config, launchers and menu xml ==")
editor.save()
config_path = paths.config_path()
check(os.path.isfile(config_path), f"config written ({config_path})")
with open(config_path, encoding="utf-8") as fh:
    saved = json.load(fh)
check([lst["name"] for lst in saved["lists"]] == ["Sculpt", "Paint"], "both lists saved")
check(any(isinstance(row, dict) and row.get("name") == "Booleans"
          for row in saved["lists"][0]["items"]), "submenu saved in the shared JSON shape")

launchers = os.listdir(paths.entry_scripts_dir())
check(sorted(launchers) == ["Paint.py", "Sculpt.py"], f"one launcher per list ({sorted(launchers)})")
xml_path = paths.menu_xml_path()
check(os.path.isfile(xml_path), "menu xml written")
with open(xml_path, encoding="utf-8") as fh:
    xml = fh.read()
check("<MenuItem>CoatMenu_Editor</MenuItem>" in xml, "editor menu item present in xml")

print("== saved config reloads into a new editor ==")
reloaded = CoatMenuEditor(config=MenuConfig.load(config_path))
reloaded.show_editor()
app.processEvents()
check([lst.name for lst in reloaded._config.lists] == ["Sculpt", "Paint"], "reload keeps lists")
check(reloaded._tree.topLevelItemCount() == len(saved["lists"][0]["items"]),
      f"reload keeps rows ({reloaded._tree.topLevelItemCount()})")
reloaded.close_editor()
editor.close_editor()

print("== panel chrome + pointer ==")
from coatmenu.ui import cursor as cursor_mod  # noqa: E402

chrome = fresh_editor()
chrome.show_editor()
app.processEvents()
start_shot = chrome.grab().toImage()
sample = start_shot.pixelColor(20, 20)
check(sample.alpha() > 200, f"panel background is painted, not transparent (alpha={sample.alpha()})")
check(sample.red() < 90 and sample.green() < 90 and sample.blue() < 90,
      f"panel background is dark (rgb={sample.getRgb()})")

cursor_mod.system_cursor_visible = lambda: False
chrome._cursor_local = QPoint(40, 40)
chrome.repaint()
app.processEvents()
with_pointer = chrome.grab().toImage()

cursor_mod.system_cursor_visible = lambda: True
chrome.repaint()
app.processEvents()
without_pointer = chrome.grab().toImage()
check(with_pointer != without_pointer,
      "editor draws its own pointer only while the system pointer is hidden")

chrome.close_editor()
check(not chrome._cursor_timer.isActive(), "pointer polling stops when the editor closes")

print()
if failures:
    print(f"EDITOR FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("EDITOR REGRESSION PASSED")
sys.exit(0)
