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

from ui import popup  # noqa: E402
from ui.popup import MenuItem, header, separator  # noqa: E402

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

print()
if failures:
    print(f"POPUP FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("POPUP REGRESSION PASSED")
sys.exit(0)
