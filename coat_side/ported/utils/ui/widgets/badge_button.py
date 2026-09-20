"""BadgeButton — re-exported from ported.lks_utils, with 3DCoat SVG helper."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from ported.lks_utils.gui_qt.widgets.badge_button import QBadgeButton

_ICON_SIZE: int = 16
_DEFAULT_COLOR: str = "#90caf9"


def _resolve_svg_path(name: str) -> Path:
    """Resolve an SVG asset path from the data directory."""
    pkg_root = Path(__file__).resolve().parent.parent.parent.parent
    return pkg_root / "ported.utils" / "ui" / "data" / f"{name}.svg"


def _make_icon_from_svg(name: str, color: str = _DEFAULT_COLOR, size: int = _ICON_SIZE) -> QIcon:
    """Render an SVG to a QIcon with the specified color."""
    svg_path: Path = _resolve_svg_path(name)
    if not svg_path.is_file():
        return QIcon()

    content: str = svg_path.read_text(encoding="utf-8")
    content = content.replace("currentColor", color)

    pixmap: QPixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer: QSvgRenderer = QSvgRenderer(content.encode("utf-8"))
    painter: QPainter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


def make_badge_button(
    icon_name: str,
    text: str = "",
    tooltip: str = "",
    color: str = _DEFAULT_COLOR,
    icon_size: int = _ICON_SIZE,
) -> QBadgeButton:
    """Create a QBadgeButton with an SVG icon from the data directory.

    Args:
        icon_name: SVG filename without extension (e.g. "invert")
        text: Button label text
        tooltip: Tooltip text
        color: CSS color for the icon (default: #90caf9 accent blue)
        icon_size: Icon size in pixels

    Returns:
        QBadgeButton instance
    """
    icon: QIcon = _make_icon_from_svg(icon_name, color=color, size=icon_size)
    return QBadgeButton(icon=icon, text=text, tooltip=tooltip, icon_size=icon_size)


__all__ = ["QBadgeButton", "make_badge_button", "_make_icon_from_svg"]
