"""
Popup tests - run offscreen, no 3DCoat needed.

Checks the parts that are pure logic or Qt plumbing: row layout, hit testing,
hover highlight, click-to-run and the trigger-key poll path.

Run:  QT_QPA_PLATFORM=offscreen python tests/test_popup.py
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
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fake_coat import install_fake_coat  # noqa: E402

DOCS = tempfile.mkdtemp(prefix="coatmenu-popup-")
FAKE = install_fake_coat(DOCS, COAT_SIDE)

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from coatmenu.ui import popup  # noqa: E402
from coatmenu.ui.popup import MenuItem, header, separator  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


def build_items() -> list[MenuItem]:
    return [
        header("Section"),
        MenuItem(label="Resample", kind="command", cid="Resample"),
        MenuItem(label="Smooth Object", kind="command", cid="SmoothObject"),
        separator(),
        MenuItem(label="Wireframe", kind="command", cid="VIEW_WIREFRAME"),
    ]


print("== layout ==")
manager = popup.get_manager()
manager.show_menu(build_items(), anchor=QPoint(120, 120), title="CoatMenu")
widget = manager.popup
check(widget is not None and widget.isVisible(), "popup is visible after show_menu")
if widget is not None:
    check(widget.pos() == QPoint(120, 120),
          f"top-left corner sits exactly on the cursor, like Krita's menu ({widget.pos()})")
    check(len(widget._rows) == 6, f"row count includes title+section headers ({len(widget._rows)})")
    check(widget.width() > 100 and widget.height() > 60,
          f"size is sane ({widget.width()}x{widget.height()})")
    check(widget.windowFlags() & Qt.FramelessWindowHint, "frameless")
    check(widget.windowFlags() & Qt.WindowStaysOnTopHint, "always on top")

    print("== hit testing ==")
    first_clickable = next(i for i, (_y, item, _h) in enumerate(widget._rows) if item.clickable)
    y = widget._rows[first_clickable][0] + 4
    check(widget._row_at(QPoint(20, y)) == first_clickable, "row hit test finds the first row")
    check(widget._row_at(QPoint(20, -5)) == -1, "hit test outside rows returns -1")

    print("== hover ==")
    widget._hover = -1
    widget.mouseMoveEvent(type("E", (), {"position": lambda _s, p=QPointF(20, y): p})())
    check(widget._hover == first_clickable, "mouse move sets hover row")

    print("== click runs the command ==")
    clicks = widget._rows[first_clickable][1]
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(20, y))
    check(FAKE.commands_run() == ["$" + clicks.cid],
          f"click executed {clicks.cid} -> {FAKE.commands_run()}")
    check(not widget.isVisible(), "popup closed after the click")

print("== click on a separator does not run anything ==")
FAKE.calls.clear()
manager.show_menu(build_items(), anchor=QPoint(120, 120), title="CoatMenu")
widget = manager.popup
sep_row = next(i for i, (_y, item, _h) in enumerate(widget._rows) if item.kind == "separator")
QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier,
                 QPoint(20, widget._rows[sep_row][0] + 2))
check(FAKE.calls == [], f"separator click is inert ({FAKE.calls})")
check(not widget.isVisible(), "separator click closes the popup")

print("== script items ==")
popup.run_item(MenuItem(label="Script", kind="script", cid="C:/tmp/foo.py"))
check(FAKE.scripts_run() == ["C:/tmp/foo.py"], "script item runs through coat.io.executeScript")

print("== trigger-key release runs the highlighted row ==")
FAKE.calls.clear()
manager.show_menu(build_items(), anchor=QPoint(120, 120), trigger_vk=0x51)
widget = manager.popup
first_clickable = next(i for i, (_y, item, _h) in enumerate(widget._rows) if item.clickable)
widget._hover = first_clickable
popup.is_key_down = lambda _vk: False  # simulate "user let go of the key"
widget._on_poll()
check(FAKE.commands_run() == ["$" + widget._rows[first_clickable][1].cid],
      f"release executed the hovered row ({FAKE.commands_run()})")

print("== escape dismisses ==")
FAKE.calls.clear()
manager.show_menu(build_items(), anchor=QPoint(120, 120), trigger_vk=0x51)
widget = manager.popup
popup.is_key_down = lambda vk: vk == popup.VK_ESCAPE
widget._on_poll()
check(not widget.isVisible() and FAKE.calls == [],
      "escape closed the popup without running anything")

print("== submenus ==")
FAKE.calls.clear()
popup.is_key_down = lambda _vk: False
sub_items = [
    header("Lists"),
    MenuItem(label="Sculpt", kind="submenu", children=[
        MenuItem(label="Resample", kind="command", cid="Resample"),
        MenuItem(label="Smooth", kind="command", cid="SmoothObject"),
    ]),
    MenuItem(label="Paint", kind="submenu", children=[
        MenuItem(label="Fill", kind="command", cid="FillLayer"),
    ]),
    MenuItem(label="Plain", kind="command", cid="PlainCmd"),
]
manager.show_menu(sub_items, anchor=QPoint(120, 120))
widget = manager.popup
app.processEvents()

branch_row = widget._first_branch()
check(branch_row >= 0, "branch row found")
check(widget._rows[branch_row][1].label == "Sculpt", "first branch is the first list")

widget._open_child(branch_row)
app.processEvents()
child = widget._child
check(child is not None and child.isVisible(), "child panel opens on a branch row")
check(child is not None and child.width() > 0, "child panel has a size")
check(child is not None and widget._child_row == branch_row, "child is bound to its parent row")
check(child is not None and len(child._rows) == 2, f"child shows the submenu rows ({child and len(child._rows)})")
check(child is not None and child.x() >= widget.x(), "child sits to the right of its parent")
check(child is not None and child.is_child, "child knows it is a child (does not run its own key poll)")

print("== clicking a child row runs it and closes the whole stack ==")
sub_item = child._rows[0][1]
QTest.mouseClick(child, Qt.LeftButton, Qt.NoModifier, QPoint(20, child._rows[0][0] + 4))
check(FAKE.commands_run() == ["$" + sub_item.cid],
      f"child click ran {sub_item.cid} ({FAKE.commands_run()})")
check(not widget.isVisible() and not child.isVisible(), "both panels closed")

print("== hovering away from a branch closes the child, grace timer ==")
manager.show_menu(sub_items, anchor=QPoint(120, 120))
widget = manager.popup
app.processEvents()
widget._open_child(widget._first_branch())
child = widget._child
plain_row = next(i for i, (_y, item, _h) in enumerate(widget._rows) if item.label == "Plain")
widget._hover = plain_row
widget.mouseMoveEvent(type("E", (), {"position": lambda _s, p=QPoint(20, widget._rows[plain_row][0] + 4): p})())
app.processEvents()
check(widget._child is None, "moving to a non-branch row closes the child panel")

print("== dismiss closes children too ==")
widget._open_child(widget._first_branch())
child = widget._child
check(child is not None and child.isVisible(), "child open again")
widget.dismiss()
app.processEvents()
check(not widget.isVisible() and (child is None or not child.isVisible()),
      "dismiss closed parent and child")

print("== a branch row is not treated as an executable action ==")
FAKE.calls.clear()
widget.show_at(QPoint(120, 120))
branch_item = widget._rows[widget._first_branch()][1]
check(not branch_item.clickable and branch_item.is_branch, "branch rows are not directly clickable")
widget._hover = widget._first_branch()
check(widget._deepest_hover() is None,
      "release with the cursor on a closed branch runs nothing")
widget.dismiss()

print("== pointer: drawn only while the system cursor is hidden ==")
# 3DCoat hides the system pointer in brush/pen modes, so the overlay draws its
# own. Detection is mocked here (offscreen has no real cursor state).
from coatmenu.ui import cursor as cursor_mod  # noqa: E402

manager.show_menu(build_items(), anchor=QPoint(120, 120))
widget = manager.popup
app.processEvents()
row_y = widget._rows[1][0] + 4
widget.mouseMoveEvent(type("E", (), {"position": lambda _s, p=QPointF(20, row_y): p})())
check(widget._cursor_local is not None and widget._cursor_local.y() == row_y,
      f"pointer position is tracked ({widget._cursor_local})")

cursor_mod.system_cursor_visible = lambda: True
widget.repaint()
app.processEvents()
visible_shot = widget.grab().toImage()

cursor_mod.system_cursor_visible = lambda: False
widget.repaint()
app.processEvents()
hidden_shot = widget.grab().toImage()

check(visible_shot != hidden_shot,
      "an arrow is drawn only when the real pointer is hidden (no double cursor)")

cursor_mod.system_cursor_visible = lambda: True
widget.leaveEvent(None)
check(widget._cursor_local is None, "leaving the panel stops drawing the pointer")
widget.dismiss()

print("== near the screen edge the panel flips to stay visible ==")
from PySide6.QtGui import QGuiApplication  # noqa: E402

area = QGuiApplication.primaryScreen().availableGeometry()
manager.show_menu(build_items(), anchor=area.bottomRight() - QPoint(6, 6))
edge = manager.popup
check(edge.x() < area.right() - 6 and edge.y() < area.bottom() - 6,
      f"flips instead of running off the screen ({edge.pos()} in {area})")
edge.dismiss()

print("== stepping aside when another application takes the foreground ==")
manager.show_menu(build_items(), anchor=QPoint(120, 120))
widget = manager.popup
check(widget.isVisible(), "overlay open")
popup.system.foreground_is_current_process = lambda: False
widget._on_poll()
check(not widget.isVisible(), "overlay closes instead of floating over the other app")
popup.system.foreground_is_current_process = lambda: True

print()
if failures:
    print(f"POPUP FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("POPUP REGRESSION PASSED")
sys.exit(0)
