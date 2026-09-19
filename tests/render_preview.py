"""
Renders the overlay offscreen against the *real* 3DCoat data on this machine and
writes the PNGs used in the README. Lets the look be reviewed without launching
3DCoat.

Writes:
* ``preview-popup.png``     - the list index (one row per configured list)
* ``preview-submenu.png``   - the index with a list opened as a child panel
* ``preview-list.png``      - a single list shown flat

Run:  QT_QPA_PLATFORM=offscreen python tests/render_preview.py
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

DOCS = os.path.join(os.path.expanduser("~"), "Documents")


def real_install_root() -> str:
    """3DCoat program folder, read from the marker 3DCoat itself writes.

    Keeps this preview machine-independent: it uses the local install rather than
    a hard-coded path.
    """
    try:
        with open(os.path.join(DOCS, "3DCoat", "executable.txt"), encoding="utf-8",
                  errors="replace") as fh:
            exe = fh.read().strip().splitlines()[0].strip()
        return os.path.dirname(exe)
    except Exception:
        return ""


FAKE = install_fake_coat(DOCS, COAT_SIDE, install_root=real_install_root())
# Never touch the extension's own data folder while rendering previews.
os.environ["COATMENU_DATA_DIR"] = tempfile.mkdtemp(prefix="coatmenu-preview-")

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

# The offscreen QPA ships no font database at all (families() == []), so text
# renders as tofu boxes unless the system fonts are loaded explicitly.
for _font_file in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/msyh.ttc"):
    if os.path.exists(_font_file):
        QFontDatabase.addApplicationFont(_font_file)
print(f"font families available: {len(QFontDatabase.families())}")

from coatmenu.core.config import starter_config  # noqa: E402
from coatmenu.core.menu_model import submenu  # noqa: E402
from coatmenu.ui import popup  # noqa: E402

OUT_DIR = os.path.join(ROOT, "docs")
os.makedirs(OUT_DIR, exist_ok=True)
PAD = 26
BACKDROP = QColor(43, 44, 47)  # stand-in for a 3DCoat viewport


def compose(path: str, panels: list) -> None:
    """Draw one or more widgets (parent first) onto a dark backdrop."""
    shots = [(w.x(), w.y(), w.grab()) for w in panels]
    min_x = min(x for x, _y, _s in shots)
    min_y = min(y for _x, y, _s in shots)
    max_x = max(x + s.width() for x, _y, s in shots)
    max_y = max(y + s.height() for _x, y, s in shots)

    canvas = QImage(max_x - min_x + PAD * 2, max_y - min_y + PAD * 2,
                    QImage.Format_ARGB32_Premultiplied)
    painter = QPainter(canvas)
    painter.fillRect(canvas.rect(), BACKDROP)
    for x, y, shot in shots:
        painter.drawPixmap(x - min_x + PAD, y - min_y + PAD, shot)
    painter.end()
    canvas.save(path)
    print(f"wrote {path}  ({canvas.width()}x{canvas.height()})")


config = starter_config(DOCS)
config.add_list("Paint")
print(f"lists: {[lst.name for lst in config.lists]}")
for lst in config.lists:
    print(f"  {lst.hotkey_id:24} {lst.name:10} {len(lst.items)} row(s)")

manager = popup.get_manager()

# Pretend 3DCoat hid the system pointer (brush mode) so the preview shows the
# overlay's own drawn arrow.
os.environ["COATMENU_FORCE_CURSOR"] = "0"

# 1. the index
index_rows = [submenu(lst.name, lst.items) for lst in config.lists]
manager.show_menu(index_rows, anchor=QPoint(80, 80), title="CoatMenu")
widget = manager.popup
app.processEvents()
# The panel's top-left corner sits on the cursor now, so that is where the drawn
# pointer belongs in the preview.
widget._cursor_local = QPoint(2, 2)
app.processEvents()
compose(os.path.join(OUT_DIR, "preview-popup.png"), [widget])

# 2. index with the first list opened as a child panel
branch_row = widget._first_branch()
widget._hover = branch_row
widget._open_child(branch_row)
app.processEvents()
child = widget._child
print(f"child panel open: {child is not None}")
if child is not None:
    compose(os.path.join(OUT_DIR, "preview-submenu.png"), [widget, child])

# 3. a single list shown flat
widget.dismiss()
app.processEvents()
manager.show_menu(config.lists[0].items, anchor=QPoint(80, 80), title=config.lists[0].name)
widget = manager.popup
app.processEvents()
compose(os.path.join(OUT_DIR, "preview-list.png"), [widget])

# 4. the editor panel
from coatmenu.ui.editor import CoatMenuEditor  # noqa: E402

editor_config = starter_config(DOCS)
editor_config.add_list("Paint")
editor = CoatMenuEditor(config=editor_config)
editor.show_editor()
editor._source_kind.setCurrentIndex(0)  # the combined 3DCoat command list
editor.reload_sources()
editor.move(QPoint(60, 60))
editor._cursor_layer.set_position(QPoint(170, 132))
app.processEvents()
compose(os.path.join(OUT_DIR, "preview-editor.png"), [editor])
editor.close_editor()
