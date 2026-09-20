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

# Tool presets, so the editor's "Tools" source has something to list.
TOOLS_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "CustomTools")
os.makedirs(TOOLS_DIR, exist_ok=True)
with open(os.path.join(TOOLS_DIR, "BaseVoxBrush.txt"), "w", encoding="utf-8") as fh:
    fh.write("tool preset\n")

# ...and one saved preset, for the "Presets" source.
PRESETS_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "Presets")
os.makedirs(PRESETS_DIR, exist_ok=True)
with open(os.path.join(PRESETS_DIR, "HS_Test.xml"), "w", encoding="utf-8") as fh:
    fh.write("<OnePreset><Name>HS_Test</Name></OnePreset>\n")
with open(os.path.join(PRESETS_DIR, "order.txt"), "w", encoding="utf-8") as fh:
    fh.write("HS_Test.xml\n")

# ...and one script, for the "Scripts" source.
SCRIPTS_DIR = os.path.join(DOCS, "3DCoat", "UserPrefs", "Scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)
with open(os.path.join(SCRIPTS_DIR, "speedup.py"), "w", encoding="utf-8") as fh:
    fh.write("# demo\n")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from coatmenu.core import paths  # noqa: E402

# Keep every write inside the temp tree - never the repository's own folders.
paths.extension_root = lambda: os.path.join(WORK, "ext")
paths.entry_scripts_dir = lambda: os.path.join(WORK, "ext", "actions", "menus")
os.makedirs(paths.entry_scripts_dir(), exist_ok=True)

from coatmenu.core.config import MenuConfig, Menu  # noqa: E402
from coatmenu.core.menu_model import MenuItem  # noqa: E402
from coatmenu.ui.editor import ROLE_CID, ROLE_KIND, CoatMenuEditor  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def fresh_editor() -> CoatMenuEditor:
    config = MenuConfig(menus=[
        Menu(name="Sculpt", items=[
            MenuItem(label="Resample", kind="command", cid="Resample"),
            MenuItem(label="Booleans", kind="submenu", children=[
                MenuItem(label="Subtract", kind="command", cid="SubtractVolume"),
            ]),
            MenuItem(label="Wireframe", kind="command", cid="VIEW_WIREFRAME"),
        ]),
        Menu(name="Paint", items=[MenuItem(label="Fill", kind="command", cid="FillLayer")]),
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
editor.add_menu()
check([lst.name for lst in editor._config.menus] == ["Sculpt", "Paint", "Details"],
      "list added")
editor._new_name.setText("Details x")
editor.rename_menu()
check("Details x" in [lst.name for lst in editor._config.menus], "list renamed")
editor.move_menu(-1)
check([lst.name for lst in editor._config.menus][1] == "Details x", "list order changed")
editor.remove_menu()
check("Details x" not in [lst.name for lst in editor._config.menus], "list removed")

print("== source catalog ==")
editor.select_menu(0)
editor._source_kind.setCurrentIndex(0)  # 3DCoat commands (the combined list)
editor.reload_sources()
combined_count = editor._source_list.count()
check(combined_count >= 2, f"combined command list populated ({combined_count})")
editor._search.setText("Resample")
editor.reload_sources()
check(editor._source_list.count() == 1, "filter narrows the list")
editor._source_list.setCurrentRow(0)
before = editor._tree.topLevelItemCount()
editor.add_source_item()
check(editor._tree.topLevelItemCount() == before + 1, "row appended to the list")
appended = editor.tree_to_items()[-1]
check("Resample" in appended.cid, f"appended entry carries the id ({appended.cid})")

editor._search.clear()
editor._source_kind.setCurrentIndex(1)  # My tools
editor.reload_sources()
check(editor._source_list.count() == 1, f"tool presets listed ({editor._source_list.count()})")

editor._source_kind.setCurrentIndex(2)  # Presets
editor.reload_sources()
check(editor._source_list.count() == 1, f"saved presets listed ({editor._source_list.count()})")
editor._source_list.setCurrentRow(0)
editor.add_source_item()
from_preset = editor.tree_to_items()[-1]
check(from_preset.kind == "preset" and from_preset.cid == "HS_Test",
      f"a row added from Presets is a preset entry ({from_preset.kind}, {from_preset.cid})")

editor._source_kind.setCurrentIndex(4)  # Scripts
editor.reload_sources()
check(editor._source_list.count() == 1, f"scripts listed ({editor._source_list.count()})")

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
check([lst["name"] for lst in saved["menus"]] == ["Sculpt", "Paint"], "both lists saved")
check(any(isinstance(row, dict) and row.get("name") == "Booleans"
          for row in saved["menus"][0]["items"]), "submenu saved in the shared JSON shape")

launchers = os.listdir(paths.entry_scripts_dir())
check(sorted(launchers) == ["CoatMenu_Paint.py", "CoatMenu_Sculpt.py"],
      f"one launcher per list, prefixed so the Scripts menu groups them ({sorted(launchers)})")

# A launcher left over from the old (unprefixed) naming must not linger, or the
# list would show up twice in 3DCoat's Scripts menu.
stale = os.path.join(paths.entry_scripts_dir(), "Sculpt.py")
with open(stale, "w", encoding="utf-8") as fh:
    fh.write("# launcher from before the prefix\n")
editor.save()
check(not os.path.exists(stale), "a launcher from the old naming is cleared out")
check(os.path.isfile(os.path.join(paths.entry_scripts_dir(), "CoatMenu_Sculpt.py")),
      "while the prefixed launcher stays put")
xml_path = paths.menu_xml_path()
check(os.path.isfile(xml_path), "menu xml written")
with open(xml_path, encoding="utf-8") as fh:
    xml = fh.read()
check("<MenuItem>CoatMenu_Editor</MenuItem>" in xml, "editor menu item present in xml")

print("== saved config reloads into a new editor ==")
reloaded = CoatMenuEditor(config=MenuConfig.load(config_path))
reloaded.show_editor()
app.processEvents()
check([lst.name for lst in reloaded._config.menus] == ["Sculpt", "Paint"], "reload keeps lists")
check(reloaded._tree.topLevelItemCount() == len(saved["menus"][0]["items"]),
      f"reload keeps rows ({reloaded._tree.topLevelItemCount()})")
reloaded.close_editor()
editor.close_editor()

print("== promoting a submenu into its own list ==")
promo = editor._config.add_menu("Promo")
promo.items = [MenuItem(label="Group  (3)", kind="submenu", children=[
    MenuItem(label="One", kind="command", cid="ONE"),
    MenuItem(label="Two", kind="command", cid="TWO")])]
editor.reload_menus()
editor.select_menu("Promo")
editor._tree.setCurrentItem(editor._tree.topLevelItem(0))
editor.promote_submenu()
check(editor._config.find("Group") is not None,
      "the submenu became a list of its own, without the row count in its name")
check([i.label for i in editor._config.find("Group").items] == ["One", "Two"],
      "and took its rows with it")
check(editor.current_menu is not None and editor.current_menu.name == "Group",
      "the editor switched to the new list")
check("END" in editor._status.text(),
      f"and says how to give it a key ({editor._status.text()})")
check(len(editor._config.find("Promo").items) == 0,
      "the row is gone from the original list")
editor.select_menu("Promo")
check(editor._tree.topLevelItemCount() == 0, "and the original list is empty in the tree")

editor._config.add_menu("Plain")
editor.reload_menus()
editor.select_menu("Plain")
editor._tree.clearSelection()
editor.promote_submenu()
check("submenu row" in editor._status.text(), "a plain row is refused with a hint")

print("== right-click menu: move a row to another list ==")
source = editor._config.add_menu("Source")
source.items = [MenuItem(label="Moveable", kind="command", cid="MOVEME"),
                MenuItem(label="Stays", kind="command", cid="STAY")]
editor._config.add_menu("Sink")
editor.reload_menus()
editor.select_menu("Source")
editor._tree.setCurrentItem(editor._tree.topLevelItem(0))

row_menu = editor._row_menu()
texts = [a.text() for a in row_menu.actions()]
move_menu = row_menu.actions()[texts.index("Move to")].menu()
check(texts[0] == "Duplicate", f"the common actions come first ({texts})")
check("Copy to" in texts and "Move to" in texts, "copy and move are both offered")
check(texts[-2:] == ["Rename", "Delete"], f"short labels at the end ({texts[-2:]})")
check(not any("this row" in t for t in texts), "no redundant 'this row' anywhere")
check(any(a.text().startswith("Sink") for a in move_menu.actions()),
      "the move submenu lists the other lists")
check(not any(a.text().startswith("Source") for a in move_menu.actions()),
      "but not the one the row is already in")

editor.move_selected_to_list("Sink")
check([i.label for i in editor._config.find("Source").items] == ["Stays"],
      "the row left the source list")
check([i.label for i in editor._config.find("Sink").items] == ["Moveable"],
      "and landed in the target list")
check(editor.current_menu is not None and editor.current_menu.name == "Sink",
      "the editor follows the row so you can see where it went")

editor.select_menu("Source")
editor.add_submenu()
sub_node = editor._tree.topLevelItem(editor._tree.topLevelItemCount() - 1)
sub_node.setText(0, "Group")
sub_node.addChild(editor._node_for(MenuItem(label="Kid", kind="command", cid="KID")))
editor._tree.setCurrentItem(sub_node)
editor.move_selected_to_list("Sink")
moved_sub = editor._config.find("Sink").items[-1]
check(moved_sub.kind == "submenu" and moved_sub.children[0].cid == "KID",
      "a moved submenu takes its children with it")

print("== right-click actions: duplicate, copy, add below ==")
editor.select_menu("Source")
editor._tree.setCurrentItem(editor._tree.topLevelItem(0))
editor.duplicate_row()
check([i.label for i in editor.tree_to_items()] == ["Stays", "Stays"],
      f"duplicate lands right below itself ({[i.label for i in editor.tree_to_items()]})")

editor.copy_selected_to_list("Sink")
check(editor._config.find("Sink").items[-1].label == "Stays", "copy reaches the target list")
check(len(editor._config.find("Source").items) == 2, "and the original stays put")

before = editor._tree.topLevelItemCount()
editor.insert_row_after("separator")
check(editor._tree.topLevelItemCount() == before + 1, "Add below inserts beside the row")
check(editor._tree.currentItem().data(0, ROLE_KIND) == "separator",
      "as the kind that was asked for")

print("== the editor opens centred ==")
from PySide6.QtGui import QGuiApplication as _QGA  # noqa: E402

centred = fresh_editor()
centred.show_editor()
app.processEvents()
_area = _QGA.primaryScreen().availableGeometry()
_want_x = max(_area.left(), int(_area.left() + (_area.width() - centred.width()) / 2))
_want_y = max(_area.top(), int(_area.top() + (_area.height() - centred.height()) / 2))
check(abs(centred.x() - _want_x) <= 2 and abs(centred.y() - _want_y) <= 2,
      f"the panel sits in the middle of the screen "
      f"({centred.x()},{centred.y()} vs {_want_x},{_want_y})")
centred.close_editor()

print("== adding many rows at once ==")
editor._config.add_menu("Bulk")
editor.reload_menus()
editor.select_menu("Bulk")
editor._source_kind.setCurrentIndex(0)
editor._search.clear()
editor.reload_sources()
shown = editor._source_list.count()
editor.add_all_sources()
check(editor._tree.topLevelItemCount() == min(shown, 200),
      f"Add all appends what the list shows ({editor._tree.topLevelItemCount()} of {shown})")
check(f"({min(shown, 200)})" in editor._add_all.text(),
      f"and the button says how many ({editor._add_all.text()})")

editor._config.add_menu("Bulk2")
editor.reload_menus()
editor.select_menu("Bulk2")
editor.reload_sources()
editor._source_list.setCurrentRow(0)
editor._source_list.item(1).setSelected(True)
editor.add_source_item()
check(editor._tree.topLevelItemCount() == 2,
      f"a multi-selection is added row for row ({editor._tree.topLevelItemCount()})")

print("== undo / redo ==")
editor._new_name.setText("Undo Test")
editor.add_menu()
editor.select_menu("Undo Test")
base_rows = editor._tree.topLevelItemCount()
editor.add_submenu()
check(editor._tree.topLevelItemCount() == base_rows + 1, "a row was added")
editor.undo()
check(editor._tree.topLevelItemCount() == base_rows,
      f"Ctrl+Z takes it back ({editor._tree.topLevelItemCount()})")
check(editor.current_menu is not None and editor.current_menu.name == "Undo Test",
      "and stays on the same menu")
editor.redo()
check(editor._tree.topLevelItemCount() == base_rows + 1,
      f"Ctrl+Shift+Z puts it back ({editor._tree.topLevelItemCount()})")
editor.undo()
check(editor._tree.topLevelItemCount() == base_rows, "and undo works again")

# A fresh editor starts with one state and nothing to undo.
fresh = fresh_editor()
fresh.undo()
check("Nothing to undo" in fresh._status.text(), "an untouched editor has nothing to undo")
fresh.close_editor()

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

layer = chrome._cursor_layer
check(layer.testAttribute(Qt.WA_TransparentForMouseEvents),
      "pointer layer is click-through (rows stay usable under it)")
check(layer.geometry().size() == chrome.rect().size(), "pointer layer covers the panel")
check(layer.isVisible(), "pointer layer is visible")

# Whether the arrow gets painted is cursor.draw's own business (it checks the
# system pointer itself, and test_catalog covers it). What belongs here is that
# the layer tracks the position and survives being painted - comparing screenshots
# was flaky: an offscreen repaint can differ by a frame anywhere.
cursor_mod.system_cursor_visible = lambda: False
layer.set_position(QPoint(40, 40))
check(layer._position == QPoint(40, 40), "the pointer layer follows the cursor")
_blank_event = type("E", (), {})()
layer.paintEvent(_blank_event)
layer.set_position(None)
layer.paintEvent(_blank_event)
check(layer._position is None, "and clears when there is no position")
check(layer.testAttribute(Qt.WA_TransparentForMouseEvents),
      "painting never blocks the rows underneath (still click-through)")

chrome.close_editor()
check(not chrome._cursor_timer.isActive(), "pointer polling stops when the editor closes")
check(layer._position is None, "the drawn pointer is cleared on close")

print("== live preview ==")
from coatmenu.ui import popup as popup_mod  # noqa: E402

editor.select_menu(0)
editor.preview_menu()
check(editor._preview is not None and editor._preview.isVisible(), "preview panel opens")
check(editor._preview._transient is False, "a preview never closes itself")
check(editor._preview._items != [], "the preview has the current rows")

popup_mod.is_key_down = lambda vk: vk == popup_mod.VK_LBUTTON
editor._preview._on_poll()
check(editor._preview.isVisible(), "a click outside does not close a preview")
popup_mod.is_key_down = lambda vk: vk == popup_mod.VK_ESCAPE
editor._preview._on_poll()
check(editor._preview.isVisible(), "escape does not close a preview either")
popup_mod.is_key_down = lambda _vk: False

editor.preview_menu()  # pressing it twice must not stack panels
panel = editor._preview
editor.close_editor()
check(panel is not None and not panel.isVisible(), "closing the editor closes the preview")
check(editor._preview is None, "and forgets it")
editor.show_editor()

print("== un-saved edits are marked in the title strip ==")
editor._dirty = False
editor._refresh_title()
check("*" not in editor._title_label.text(), f"clean title ({editor._title_label.text()!r})")
editor.add_separator()
check("*" in editor._title_label.text(),
      f"an edit marks the title ({editor._title_label.text()!r})")
editor.save()
check("*" not in editor._title_label.text(), "saving clears the mark")

print("== the delete key removes the selected row ==")
editor._tree.setCurrentItem(editor._tree.topLevelItem(0))
rows_before_delete = editor._tree.topLevelItemCount()
editor.keyPressEvent(type("E", (), {
    "key": lambda _s: Qt.Key_Delete,
    "modifiers": lambda _s: Qt.NoModifier,
})())
check(editor._tree.topLevelItemCount() == rows_before_delete - 1,
      f"Delete removed the selected row ({editor._tree.topLevelItemCount()})")

print()
if failures:
    print(f"EDITOR FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("EDITOR REGRESSION PASSED")
sys.exit(0)
