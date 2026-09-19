"""
Renders the popup offscreen against the *real* 3DCoat data on this machine and
writes PNG previews (default + hover). Used to show the look without launching
3DCoat.

Run:  QT_QPA_PLATFORM=offscreen python tests/render_preview.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COAT_SIDE = os.path.join(ROOT, "coat_side")
sys.path.insert(0, HERE)
sys.path.insert(0, COAT_SIDE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fake_coat import install_fake_coat  # noqa: E402

DOCS = os.path.join(os.path.expanduser("~"), "Documents")
FAKE = install_fake_coat(DOCS, COAT_SIDE)

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFontDatabase, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

# The offscreen QPA ships no font database at all (families() == []), so text
# would render as tofu boxes; load the system fonts explicitly for the preview.
for _font_file in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/msyh.ttc"):
    if os.path.exists(_font_file):
        QFontDatabase.addApplicationFont(_font_file)
print(f"font families available: {len(QFontDatabase.families())}")

from core import menu_data  # noqa: E402
from ui import popup  # noqa: E402

OUT_DIR = os.path.join(ROOT, "docs")
os.makedirs(OUT_DIR, exist_ok=True)

items = menu_data.demo_items()
print(f"rows from real data: {len(items)}")
for item in items:
    print(f"  [{item.kind:9}] {item.label or ''} {item.cid}")

manager = popup.get_manager()
manager.show_menu(items, anchor=QPoint(80, 80), title="CoatMenu")
widget = manager.popup
app.processEvents()

PAD = 26


def compose(path: str) -> None:
    shot = widget.grab()
    canvas = QImage(shot.width() + PAD * 2, shot.height() + PAD * 2, QImage.Format_ARGB32_Premultiplied)
    painter = QPainter(canvas)
    # stand-in for a 3DCoat viewport (dark grey)
    painter.fillRect(canvas.rect(), QColor(43, 44, 47))
    painter.drawPixmap(PAD, PAD, shot)
    painter.end()
    canvas.save(path)
    print(f"wrote {path}")


compose(os.path.join(OUT_DIR, "preview-popup.png"))

# hovered state: highlight the first clickable row (set_items already picks it,
# so blank it first to make the two previews actually differ)
widget._hover = -1
widget.repaint()
app.processEvents()
compose(os.path.join(OUT_DIR, "preview-popup-no-hover.png"))
