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

import math

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
from coatmenu.ui import theme  # noqa: E402
from coatmenu.ui.popup import (  # noqa: E402
    COMMAND,
    PIE,
    TITLE,
    MenuItem,
    header,
    run_item,
    separator,
    submenu,
)

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

print("== releasing the hotkey leaves the menu open (it is a click menu now) ==")
FAKE.calls.clear()
manager.show_menu(build_items(), anchor=QPoint(120, 120), trigger_vk=0x51)
widget = manager.popup
first_clickable = next(i for i, (_y, item, _h) in enumerate(widget._rows) if item.clickable)
widget._hover = first_clickable
popup.is_key_down = lambda _vk: False  # the user let go of the hotkey
widget._on_poll()
check(widget.isVisible(), "letting go of the hotkey no longer closes the menu")
check(FAKE.commands_run() == [], f"and release runs nothing ({FAKE.commands_run()})")

print("== a click away from the menu closes it ==")
popup.is_key_down = lambda vk: vk == popup.VK_LBUTTON
check(widget._click_outside(QPoint(widget.x() + 5, widget.y() + 5)) is False,
      "a click inside the panel keeps it open")
check(widget._click_outside(QPoint(widget.x() - 400, widget.y() - 400)) is True,
      "a click away from the panel closes the menu")
popup.is_key_down = lambda _vk: False
check(widget._click_outside(QPoint(widget.x() - 400, widget.y() - 400)) is False,
      "without a button press nothing closes")
widget._on_poll()
check(widget.isVisible() and FAKE.commands_run() == [],
      "the menu survives a poll with no input")
widget.dismiss()

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
check(child is not None and widget._child_index == branch_row, "child is bound to its parent row")
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

print("== pie layout ==")
pie_items = [
    MenuItem(label="Top", kind=COMMAND, cid="PIE_TOP"),
    MenuItem(label="Right", kind=COMMAND, cid="PIE_RIGHT"),
    submenu("Big", [MenuItem(label=f"Leaf{i}", kind=COMMAND, cid=f"PIE_LEAF{i}")
                    for i in range(4)]),
    submenu("Pair", [MenuItem(label="A", kind=COMMAND, cid="PIE_A"),
                     MenuItem(label="B", kind=COMMAND, cid="PIE_B")]),
]
manager.show_menu(pie_items, anchor=QPoint(300, 300), title="Wheel", mode="pie")
pie = manager.popup
app.processEvents()
check(pie._mode == PIE, "popup switched to pie mode")

# A pie wraps around the cursor: the panel's middle is the trigger point, so every
# slot is the same distance away (and the pointer sits in the centre ring).
_want_x = 300 - pie.width() // 2
_want_y = 300 - pie.height() // 2
check(abs(pie.x() - _want_x) <= 2 and abs(pie.y() - _want_y) <= 2,
      f"the pie is centred on the cursor ({pie.x()},{pie.y()} vs {_want_x},{_want_y})")
check(pie._centre_point() == QPoint(pie.width() // 2, pie.height() // 2),
      "and the panel's own centre is its middle")

check(len(pie._pie_items) == 4, f"one slot per item ({len(pie._pie_items)})")
check(len(pie._pie_rects) == 4, "each slot has geometry")
check(pie._slot_expanded(3) and not pie._slot_expanded(2),
      "a small group draws its children in place, a big one does not")
check([len(r) for r in pie._pie_rects] == [1, 1, 1, 2],
      f"only the small group stacks buttons ({[len(r) for r in pie._pie_rects]})")
check([t.label for t in pie._slot_targets(3)] == ["A", "B"],
      "stacked buttons carry the children, in order")
check(pie._title == "Wheel", "the list name is still remembered")
check(not any(item.kind == TITLE for item in pie._items),
      "a pie has no title row (Blender-style: no centre caption)")
check(pie._hover == -1, "a pie starts with nothing pre-selected")

centre = pie._centre_point()
# Auto spreads four slots onto up / right / down / left - a layout your hand can
# learn, rather than the four corners (which is where (index + 0.5) put them).
for index, sx, sy in ((0, 0, -1), (1, 1, 0), (2, 0, 1), (3, -1, 0)):
    point = pie._slot_centre(index)
    dx = point.x() - centre.x()
    dy = point.y() - centre.y()
    # A stacked slot's bounding box straddles the gap between its buttons, so
    # hit-test the first button itself rather than the slot centre.
    first_button = pie._slot_rects(index)[0]
    hit_point = QPoint(int(first_button.center().x()), int(first_button.center().y()))
    check(pie._pie_index_at(hit_point) == index,
          f"slot {index} hit-tests to itself ({pie._pie_index_at(hit_point)})")
    if sx == 0:
        check(abs(dx) < 2 and dy * sy > 0,
              f"slot {index} sits straight {'up' if sy < 0 else 'down'} ({dx:.0f}, {dy:.0f})")
    elif sy == 0:
        check(abs(dy) < 2 and dx * sx > 0,
              f"slot {index} sits straight {'right' if sx > 0 else 'left'} ({dx:.0f}, {dy:.0f})")
    else:
        check(dx * sx > 0 and dy * sy > 0,
              f"slot {index} sits in its own direction ({dx:.0f}, {dy:.0f})")
    reach = math.hypot(dx, dy)
    check(abs(reach - pie._slot_distance) < 8,
          f"button {index} sits one pie radius out ({reach:.0f}px)")
check(pie._slot_distance > theme.PIE_SLOT_DISTANCE - 1,
      f"the ring grows past Blender's 100px when labels are wide ({pie._slot_distance:.0f}px)")
for index in range(len(pie._pie_items)):
    first = pie._slot_rect(index)
    second = pie._slot_rect((index + 1) % len(pie._pie_items))
    check(not first.intersects(second),
          f"buttons {index} and {(index + 1) % len(pie._pie_items)} do not overlap")
check(pie._pie_index_at(QPoint(int(centre.x()), int(centre.y()))) == -1,
      "the centre ring selects nothing")
check(pie._pie_index_at(QPoint(int(centre.x()), int(centre.y() - 200))) == -1,
      "empty space between the buttons selects nothing")

pie_shot = pie.grab()
check(not pie_shot.isNull() and pie_shot.width() > 100,
      f"the pie paints ({pie_shot.width()}x{pie_shot.height()})")

print("== pie: resting on a branch unfolds its submenu, release runs the segment ==")
pie._hover = 2
pie._dwell.timeout.emit()  # what the dwell timer fires after PIE_DWELL_MS
app.processEvents()
check(pie._child is not None and pie._child.isVisible(), "dwell opened the branch submenu")
check(pie._child_index == 2, "submenu bound to its segment")
pie._hover = 0
check(pie._deepest_hover() is not None and pie._deepest_hover().cid == "PIE_TOP",
      "release over a segment runs that command")

print("== hovering one stacked button does not light the whole group ==")
second_rect = pie._slot_rects(3)[1]
centre = second_rect.center().toPoint()
check(pie._pie_hit(centre) == (3, 1),
      f"the second button is hit on its own ({pie._pie_hit(centre)})")
pie._hover, pie._hover_button = 3, 1
check(pie._hover_item() is pie._slot_targets(3)[1],
      "and the hovered entry follows the button, not the whole slot")
pie._hover, pie._hover_button = 3, 0
check(pie._hover_item() is pie._slot_targets(3)[0], "button 0 gives the first child")

print("== pie: a stacked slot runs the button you clicked ==")
FAKE.calls.clear()
pair_rect = pie._slot_rects(3)[1]  # the "B" button of the stacked slot
QTest.mouseClick(pie, Qt.LeftButton, Qt.NoModifier,
                 QPoint(int(pair_rect.center().x()), int(pair_rect.center().y())))
check(FAKE.commands_run() == ["$PIE_B"],
      f"clicking the second stacked button ran it ({FAKE.commands_run()})")

print("== pie: the digit keys run a button outright (Blender's shortcut hints) ==")
manager.show_menu(pie_items, anchor=QPoint(300, 300), title="Wheel", mode="pie")
pie = manager.popup
app.processEvents()
FAKE.calls.clear()
real_key_down = popup.is_key_down
popup.is_key_down = lambda vk: vk == popup.VK_1
try:
    handled = pie._check_digits()
finally:
    popup.is_key_down = real_key_down
check(handled, "pressing 1 is handled")
check(FAKE.commands_run() == ["$PIE_TOP"],
      f"key 1 ran the first button ({FAKE.commands_run()})")
check(not pie.isVisible(), "the pie closed after the shortcut ran")

manager.show_menu(pie_items, anchor=QPoint(300, 300), title="Wheel", mode="pie")
pie = manager.popup
app.processEvents()
FAKE.calls.clear()
popup.is_key_down = lambda vk: vk == popup.VK_1 + 3  # the "4" key
try:
    pie._check_digits()
finally:
    popup.is_key_down = real_key_down
check(FAKE.commands_run() == ["$PIE_A"],
      f"a digit aimed at a stacked slot runs its first button ({FAKE.commands_run()})")

print("== a multi-command row fires its commands in order ==")
from coatmenu.core.menu_model import (  # noqa: E402
    COMMAND, EXPAND_AUTO, EXPAND_INLINE, EXPAND_PANEL, POSITION_LEFT, POSITION_MODES, POSITION_TOP,
    SUBMENU, MenuItem, sequence,
)

FAKE.calls.clear()
run_item(sequence("Cube", ["$SCULPT_TRANSFORM", "$SCULP_PRIM",
                           "$VoxelSculptTool::prm_CubPrim"]))
expected = ["$SCULPT_TRANSFORM", "$SCULP_PRIM", "$VoxelSculptTool::prm_CubPrim"]
check(FAKE.commands_run() == expected,
      f"all three commands ran, in order ({FAKE.commands_run()})")

print("== long lists scroll; arrows and Enter drive the menu ==")
long_rows = [MenuItem(label=f"Entry {i:02d}", kind=COMMAND, cid=f"CMD{i}")
             for i in range(40)]
manager.show_menu(long_rows, anchor=QPoint(120, 120), title="Long")
widget = manager.popup
app.processEvents()
check(widget.height() <= theme.MAX_MENU_HEIGHT, f"the panel is capped ({widget.height()}px)")
check(widget._content_height > widget.height(), "the rows are taller than the panel")
check(widget._scroll_max > 0, f"so it knows it must scroll ({widget._scroll_max}px)")

check(widget._row_at(QPoint(10, 10)) == 0, "the first row is reachable before scrolling")
widget.wheelEvent(type("E", (), {"angleDelta": lambda _s: QPoint(0, -120)})())
check(widget._scroll > 0, f"the wheel scrolls ({widget._scroll}px)")
widget._scroll = 0

kept_key_down = popup.is_key_down
start = widget._hover
popup.is_key_down = lambda vk: vk == popup.VK_DOWN
widget._on_poll()
popup.is_key_down = lambda _vk: False
widget._on_poll()
check(widget._hover == start + 1, f"down-arrow moved the highlight ({widget._hover})")
popup.is_key_down = lambda vk: vk == popup.VK_UP
widget._on_poll()
popup.is_key_down = lambda _vk: False
widget._on_poll()
check(widget._hover == start, f"up-arrow came back ({widget._hover})")

FAKE.calls.clear()
popup.is_key_down = lambda vk: vk == popup.VK_RETURN
widget._on_poll()
popup.is_key_down = kept_key_down
check(FAKE.commands_run() == ["$CMD0"],
      f"enter ran the highlighted row ({FAKE.commands_run()})")
check(not widget.isVisible(), "and the menu closed")

print("== a digit also works in a list (same indexing as the pie) ==")
manager.show_menu(long_rows, anchor=QPoint(120, 120), title="Long")
widget = manager.popup
app.processEvents()
FAKE.calls.clear()
popup.is_key_down = lambda vk: vk == popup.VK_1 + 2  # the "3" key
widget._on_poll()
popup.is_key_down = kept_key_down
check(FAKE.commands_run() == ["$CMD2"],
      f"digit 3 ran the third row ({FAKE.commands_run()})")

print("== escape closes a submenu before the menu ==")
manager.show_menu(sub_items, anchor=QPoint(120, 120), title="Levels")
widget = manager.popup
app.processEvents()
widget._open_child(widget._first_branch())
app.processEvents()
check(widget._child is not None and widget._child.isVisible(), "child open")
popup.is_key_down = lambda vk: vk == popup.VK_ESCAPE
widget._on_poll()
popup.is_key_down = lambda _vk: False
widget._on_poll()
check(widget._child is None and widget.isVisible(),
      "first escape closes the child, the menu stays")
popup.is_key_down = lambda vk: vk == popup.VK_ESCAPE
widget._on_poll()
popup.is_key_down = kept_key_down
check(not widget.isVisible(), "second escape closes the menu")

print("== Expand pins a pie slot either way ==")
def _pie(expand):
    kids = [MenuItem(label=f"k{i}", kind=COMMAND, cid=f"c{i}")
            for i in range(4)]           # 4 children: over PIE_INLINE_MAX
    item = MenuItem(label="G", kind=SUBMENU, children=kids,
                              expand=expand)
    mgr = popup.get_manager()
    mgr.show_menu([item], anchor=QPoint(200, 200), title="T", mode="pie")
    app.processEvents()
    w = mgr.popup
    expanded = list(w._pie_expanded)
    w.dismiss()
    return expanded

check(_pie(EXPAND_INLINE) == [True],
      "Inline forces 4 children into the slot")
check(_pie(EXPAND_PANEL) == [False],
      "Panel forces a separate panel")
check(_pie(EXPAND_AUTO) == [False],
      "Auto still says panel for 4")
small = [MenuItem(label=f"s{i}", kind=COMMAND, cid=f"d{i}")
         for i in range(2)]                # 2 children: under the limit
auto_item = MenuItem(label="S", kind=SUBMENU, children=small)
mgr2 = popup.get_manager()
mgr2.show_menu([auto_item], anchor=QPoint(200, 200), title="T", mode="pie")
app.processEvents()
w2 = mgr2.popup
check(list(w2._pie_expanded) == [True], "Auto keeps small groups inline")
w2.dismiss()

print("== Where pins a slot to a compass point ==")
pinned_items = [
    MenuItem(label="pinned-left", kind="command", cid="a", position=POSITION_LEFT),
    MenuItem(label="pinned-top", kind="command", cid="b", position=POSITION_TOP),
    MenuItem(label="free", kind="command", cid="c"),
]
mgr4 = popup.get_manager()
mgr4.show_menu(pinned_items, anchor=QPoint(300, 300), title="W", mode="pie")
app.processEvents()
pinned = mgr4.popup
_c = pinned._centre_point()
_l = pinned._slot_centre(pinned._pie_items.index(
    [i for i in pinned._pie_items if i.label == "pinned-left"][0]))
_t = pinned._slot_centre(pinned._pie_items.index(
    [i for i in pinned._pie_items if i.label == "pinned-top"][0]))
check(_l.x() < _c.x() - 20 and abs(_l.y() - _c.y()) < 3,
      f"a row pinned Left lands straight left ({_l.x() - _c.x():.0f}, {_l.y() - _c.y():.0f})")
check(abs(_t.x() - _c.x()) < 3 and _t.y() < _c.y() - 20,
      f"a row pinned Top lands straight up ({_t.x() - _c.x():.0f}, {_t.y() - _c.y():.0f})")
check(pinned._slot_angle(2) == 2 * 360.0 / 3,
      f"an Auto row still spreads evenly ({pinned._slot_angle(2):.1f} deg)")
pinned.dismiss()

print("== a launcher opens the menu it names ==")
# Two names that slugify the same: the second one's launcher calls
# show_list('<its own slug>'), and that has to reach the second menu - matching the
# plain slug handed back the first one, or nothing at all.
import json  # noqa: E402

from coatmenu.core import show as show_mod  # noqa: E402

clash_dir = tempfile.mkdtemp(prefix="coatmenu-clash-data-")
os.environ["COATMENU_DATA_DIR"] = clash_dir
with open(os.path.join(clash_dir, "menus.json"), "w", encoding="utf-8") as fh:
    json.dump({"version": 1, "menus": [
        {"name": "Cut & Fill", "items": [{"id": "Resample", "label": "first-menu"}]},
        {"name": "Cut__Fill", "items": [{"id": "Bevel", "label": "second-menu"}]},
    ]}, fh)
show_mod.show_list("Cut_Fill-2")
clash_popup = popup.get_manager().popup
check(clash_popup is not None and clash_popup._title == "Cut__Fill",
      f"the second menu opens, not the first ({getattr(clash_popup, '_title', None)})")
check(clash_popup is not None
      and "second-menu" in [row[1].label for row in clash_popup._rows],
      "with the second menu's own rows")
popup.hide_menu()

print("== a menu that hangs off the screen is pulled back on ==")
# A cursor can sit where no screen is - the gap in an L-shaped desktop, or a display
# that has just gone away. The panel has to land on the screen we picked anyway, or
# the menu is simply invisible.
from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

area = QGuiApplication.primaryScreen().availableGeometry()
manager.show_menu(build_items(), anchor=QPoint(area.center().x(), area.center().y()),
                  title="CoatMenu")
app.processEvents()
widget = manager.popup
widget.setFixedSize(180, 180)


def placed(anchor: QPoint) -> QPoint:
    return widget._clamped_position(anchor)


dead_zone = placed(QPoint(area.left() - 1500, area.top() + 40))
check(area.contains(dead_zone) and area.contains(dead_zone + QPoint(179, 179)),
      f"an anchor on no screen still lands on one ({dead_zone.x()},{dead_zone.y()})")
bottom = placed(QPoint(area.center().x(), area.bottom() - 5))
check(bottom.y() < area.bottom() - 5,
      f"at the bottom edge the panel flips above the cursor ({bottom.y()})")
right = placed(QPoint(area.right() - 5, area.center().y()))
check(right.x() < area.right() - 5,
      f"at the right edge it flips to the left of the cursor ({right.x()})")
middle = placed(QPoint(area.center().x(), area.center().y()))
check(middle == QPoint(area.center().x(), area.center().y()),
      "in the middle it hangs from the cursor, the way a context menu does")
tall = QPoint(area.center().x(), area.bottom() - 20)
widget.setFixedSize(180, area.height() + 400)
check(placed(tall).y() == area.top(),
      f"a panel taller than the screen is pinned to the top ({placed(tall).y()})")

print("== a list longer than the screen scrolls ==")
long_items = [MenuItem(label=f"row {i:02d}", kind="command", cid=f"CMD{i:02d}")
              for i in range(60)]
manager.show_menu(long_items, anchor=QPoint(area.left() + 20, area.top() + 20), title="L")
app.processEvents()
widget = manager.popup
limit = widget._viewport_limit()
check(widget.height() <= limit, f"height {widget.height()} respects the cap {limit}")
check(widget._scroll_max == widget._content_height - widget.height() > 0,
      f"and there is something to scroll ({widget._scroll_max} of {widget._content_height})")
check(widget._row_at(QPoint(6, theme.PADDING + 1)) >= 0,
      "a click inside the first row hits it")
check(widget._row_at(QPoint(6, 1)) == -1,
      "the padding above the first row hits nothing")
widget._scroll = widget._scroll_max
_y, _item, _h = widget._rows[-1]
check(widget._row_at(QPoint(6, _y + _h - widget._scroll - 1)) == len(widget._rows) - 1,
      "and hit testing follows the scroll to the last row")
check(widget._row_at(QPoint(6, widget.height() - 1)) == -1,
      "the padding after the last row hits nothing, so that click closes the menu")

print("== the highlight never parks on a header or separator ==")
# Arrow keys walk the rows; a header or a separator is not a target, so the
# highlight has to step over them - landing on one would look like a stuck menu.
mixed = ([header("Group")]
         + [MenuItem(label=f"a {i}", kind="command", cid=f"A{i}") for i in range(3)]
         + [separator()]
         + [MenuItem(label=f"b {i}", kind="command", cid=f"B{i}") for i in range(3)])
manager.show_menu(mixed, anchor=QPoint(60, 60), title="")
app.processEvents()
widget = manager.popup
visited = []
stuck = []
for _step in range(len(widget._rows) * 2 + 2):
    widget._move_hover(1)
    _y, item, _h = widget._rows[widget._hover]
    visited.append(item.label)
    if not (item.clickable or item.is_branch):
        stuck.append(item.label)
check(not stuck, f"it never lands on a header or separator ({sorted(set(stuck))})")
check(sorted(set(visited)) == ["a 0", "a 1", "a 2", "b 0", "b 1", "b 2"],
      f"and it cycles through every clickable row ({sorted(set(visited))})")
popup.hide_menu()

print("== the height cap follows the screen the menu opens on ==")
# A second monitor is usually a different height: a list laid out for the primary
# screen and shown on a shorter one would leave its last rows off the bottom.
class FakeScreen:
    def __init__(self, height: int) -> None:
        self._rect = QRect(0, 0, 1920, height)

    def availableGeometry(self) -> QRect:
        return self._rect


short = FakeScreen(600)
check(widget._viewport_limit(short) == min(theme.MAX_MENU_HEIGHT, int(600 * 0.85)),
      f"a short screen caps it ({widget._viewport_limit(short)})")
check(widget._viewport_limit(FakeScreen(2160)) > widget._viewport_limit(short),
      "a tall one allows more")
check(widget._viewport_limit() == widget._viewport_limit(QGuiApplication.primaryScreen()),
      "with no argument it is the screen this panel opens on")
grown = widget.height()
widget._screen_for = lambda anchor=None: short
widget._fit_height()
check(widget.height() <= widget._viewport_limit(short),
      f"opening on the shorter screen shrinks it ({grown} -> {widget.height()})")
check(widget._scroll_max == widget._content_height - widget.height(),
      f"and the scroll range follows ({widget._scroll_max})")
popup.hide_menu()

print("== a menu with nothing to click is inert, not broken ==")
manager.show_menu([header("Nothing here"), separator()], anchor=QPoint(60, 60), title="")
app.processEvents()
widget = manager.popup
check(widget._first_interactive() == -1, "nothing is pre-selected")
FAKE.calls.clear()
widget._move_hover(1)
widget._activate_hover()
check(FAKE.calls == [], f"moving and activating do nothing ({FAKE.calls})")
popup.hide_menu()
manager.show_menu([], anchor=QPoint(60, 60))
app.processEvents()
check(manager.popup is not None, "and an empty menu still opens")
popup.hide_menu()

print("== a submenu chain: one child at a time, beside its own parent ==")
# Offscreen there is no cursor, so the poll timer closes a child as soon as it ticks
# (it asks whether the cursor is still over the panel). Freeze the timers for the
# chain while checking geometry; the timer behaviour itself is checked below.
def freeze(panel) -> None:
    for node in panel.child_panels():
        node._poll.stop()
        node._grace.stop()


def branch_index(panel, label: str) -> int:
    for index, item in enumerate(panel._items):
        if item.is_branch and item.label == label:
            return index
    raise AssertionError(f"no branch {label!r} in {[i.label for i in panel._items]}")


def chained() -> list[MenuItem]:
    return [
        header("Top"),
        MenuItem(label="Plain", kind="command", cid="Resample"),
        submenu("Level 1", [
            MenuItem(label="one", kind="command", cid="Resample"),
            submenu("Level 2", [MenuItem(label="two", kind="command", cid="Bevel")]),
            submenu("Level 2 wide",
                    [MenuItem(label="w" * 40, kind="command", cid="Bevel"),
                     MenuItem(label="wide two", kind="command", cid="Bevel")]),
        ]),
        submenu("Other group", [MenuItem(label="elsewhere", kind="command", cid="Bevel")]),
    ]


def open_chain_root(x: int, y: int):
    manager.show_menu(chained(), anchor=QPoint(x, y), title="Root")
    app.processEvents()
    panel = manager.popup
    panel.move(x + 20, y + 20)
    freeze(panel)
    return panel


screen = QGuiApplication.primaryScreen().availableGeometry()
root = open_chain_root(screen.left() + 20, screen.top() + 20)
level1 = branch_index(root, "Level 1")
root._open_child(level1)
app.processEvents()
freeze(root)
child = root._child
check(child is not None and child.isVisible(), "a branch opens a child")
check(len(root.child_panels()) == 2, f"one child at a time ({len(root.child_panels())})")
child_box = child.geometry()
check(child_box.left() >= screen.left() and child_box.top() >= screen.top(),
      f"the child is on screen ({child_box.left()},{child_box.top()})")
check(child.x() >= root.x() + root.width() - theme.SUBMENU_OVERLAP - 1
      or child.x() + child.width() <= root.x() + theme.SUBMENU_OVERLAP + 1,
      f"and beside the parent, not over it ({child.x()} vs {root.x()})")
check(abs(child.y() - (root.y() + root._rows[level1][0] - theme.PADDING)) <= 1
      or child.y() == max(screen.top(), screen.bottom() - child.height()),
      f"lined up with the parent row ({child.y()})")

first_child = child
root._open_child(branch_index(root, "Other group"))
app.processEvents()
freeze(root)
check(root.child_panels()[1] is not first_child, "hovering another branch re-targets it")
check(not first_child.isVisible(), "and the first child is gone")

root._open_child(level1)
app.processEvents()
freeze(root)
child = root._child
child._open_child(branch_index(child, "Level 2"))
app.processEvents()
freeze(root)
grand = child._child
check(grand is not None and len(root.child_panels()) == 3,
      f"a child has children ({len(root.child_panels())} deep)")
check(grand.x() >= child.x() + child.width() - theme.SUBMENU_OVERLAP - 1
      or grand.x() + grand.width() <= child.x() + theme.SUBMENU_OVERLAP + 1,
      f"beside its own parent, not the root ({grand.x()} vs {child.x()})")

print("== Escape backs out one level per press ==")
root._escape()
app.processEvents()
check(len(root.child_panels()) == 2 and not grand.isVisible(),
      f"Escape closes only the innermost panel ({len(root.child_panels())})")
check(child.isVisible(), "its parent stays")
root._escape()
app.processEvents()
check(len(root.child_panels()) == 1 and root.isVisible(),
      f"then that one ({len(root.child_panels())})")
root._escape()
app.processEvents()
check(not root.isVisible(), "then the menu itself")

print("== a wide child under a parent at the edge stays on screen ==")
# The child opens to the right of its parent and flips left when it does not fit -
# which, under a parent already at the left edge, used to put it off the screen.
root = open_chain_root(screen.left(), screen.top() + 20)
node = root
for label in ("Level 1", "Level 2 wide"):
    node._open_child(branch_index(node, label))
    app.processEvents()
    freeze(root)
    node = node._child
    check(node is not None, f"{label} opened")
wide = node.geometry()
check(wide.left() >= screen.left() and wide.right() <= screen.right(),
      f"it stays inside the screen horizontally ({wide.left()}..{wide.right()})")
check(wide.top() >= screen.top() and wide.bottom() <= screen.bottom(),
      f"and vertically ({wide.top()}..{wide.bottom()})")

print("== a child longer than the screen scrolls ==")
long_child = submenu("Long", [MenuItem(label=f"row {i:02d}", kind="command", cid="Bevel")
                              for i in range(60)])
manager.show_menu([long_child], anchor=QPoint(screen.left() + 30, screen.top() + 30), title="")
app.processEvents()
root = manager.popup
freeze(root)
root._open_child(root._first_interactive())
app.processEvents()
freeze(root)
child = root._child
check(child is not None and child.height() <= child._viewport_limit(),
      f"it respects the viewport cap ({getattr(child, 'height', lambda: '?')()})")
check(child.y() >= screen.top() and child.y() + child.height() <= screen.bottom() + 1,
      f"and is inside the screen ({child.y()} + {child.height()})")
check(child._scroll_max > 0, f"so it scrolls instead ({child._scroll_max})")

print("== the grace window is what holds a child open ==")
root = open_chain_root(screen.left() + 30, screen.top() + 30)
root._open_child(branch_index(root, "Level 1"))
app.processEvents()
freeze(root)
child = root._child
check(not root._grace.isActive(), "no grace while the child is open and unhovered")
root.leaveEvent(None)
check(root._grace.isActive(), "leaving the panel starts the grace window")
root.enterEvent(None)
check(not root._grace.isActive(), "coming back cancels it")
child._cancel_grace()
check(not child._grace.isActive(), "a child cancels its own on enter")

print("== picking a row inside a child runs it and closes the lot ==")
root = open_chain_root(screen.left() + 30, screen.top() + 30)
root._open_child(branch_index(root, "Level 1"))
app.processEvents()
freeze(root)
child = root._child
FAKE.calls.clear()
child._hover = [index for index, item in enumerate(child._items) if item.label == "one"][0]
child._activate_hover()
check(FAKE.commands_run() == ["$Resample"],
      f"the nested entry ran its command ({FAKE.commands_run()})")
check(not root.isVisible(), "and the whole menu closed, not just that panel")
popup.hide_menu()

if failures:
    print(f"POPUP FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("POPUP REGRESSION PASSED")
sys.exit(0)
