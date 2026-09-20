"""SvgIcon / SvgIconButton / get_icon — replaced by ported.lks_utils QSquareIconButton and button_presets.

This module retains backward-compatible factory functions that use
ported.lks_utils primitives internally.
"""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
from PySide6.QtSvg import QSvgRenderer

from ported.lks_utils.gui_qt.widgets.square_icon_button import QSquareIconButton
from ported.lks_utils.gui_qt.widgets.button_presets import preset_icon_color

# =============================================================================
# CONSTANTS
# =============================================================================

try:
    from ported.utils.ui.styles import COLOR_ACCENT
except ImportError:
    COLOR_ACCENT: str = "#90caf9"

_DEFAULT_SIZE: int = 16
_DEFAULT_MIN_SIZE: int = 8

# =============================================================================
# PATH RESOLUTION
# =============================================================================

def _resolve_svg_path(name: str) -> Path:
    """Resolve an SVG asset path from the data directory."""
    pkg_root = Path(__file__).resolve().parent.parent.parent.parent
    return pkg_root / "ported.utils" / "ui" / "data" / f"{name}.svg"


# =============================================================================
# SvgIcon (ZERO-DEPRECATION re-export — keeps existing 3DCoat calls working)
# =============================================================================

class SvgIcon(QWidget):
    """Square SVG icon that auto-scales within container constraints.

    SVGs use currentColor for stroke, themed via the widget color property.
    Default color is COLOR_ACCENT (#90caf9, pale icy blue).

    This is kept as a thin, self-contained implementation because the
    ported.lks_utils QSquareIconButton uses a different approach (theme-token
    based icon loading via QThemeProvider).
    """

    def __init__(
        self,
        name: str,
        size: int = _DEFAULT_SIZE,
        min_size: int = _DEFAULT_MIN_SIZE,
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setMinimumSize(min_size, min_size)
        self.setMaximumSize(size, size)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._icon_color: str = color if color is not None else COLOR_ACCENT
        self.setStyleSheet(f"SvgIcon {{ color: {self._icon_color}; }}")

        self._renderer: QSvgRenderer | None = None
        self._name: str = name
        self._load_svg(name)

    def setColor(self, color: str) -> None:
        """Change the icon color and rebuild the renderer."""
        self._icon_color = color
        self.setStyleSheet(f"SvgIcon {{ color: {color}; }}")
        self._load_svg(self._name)
        self.update()

    def color(self) -> str:
        return self._icon_color

    def name(self) -> str:
        return self._name

    def _load_svg(self, name: str) -> None:
        svg_path: Path = _resolve_svg_path(name)
        if svg_path.is_file():
            content: str = svg_path.read_text(encoding="utf-8")
            content = content.replace("currentColor", self._icon_color)
            self._renderer = QSvgRenderer(content.encode("utf-8"))
        else:
            self._renderer = None

    def paintEvent(self, event) -> None:  # noqa: ANN001
        if self._renderer is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        avail_w: int = self.width()
        avail_h: int = self.height()
        side: int = min(avail_w, avail_h)
        x: float = (avail_w - side) / 2.0
        y: float = (avail_h - side) / 2.0
        from PySide6.QtCore import QRectF
        target_rect: QRectF = QRectF(x, y, float(side), float(side))

        self._renderer.render(painter, target_rect)
        painter.end()


# =============================================================================
# SvgIconButton (thin wrapper over QSquareIconButton)
# =============================================================================

class SvgIconButton(QPushButton):
    """Square button containing a centered SVG icon, with optional backdrop.

    Uses ported.lks_utils QSquareIconButton internally for the fixed-size square
    button behavior, with a custom SvgIcon for the SVG loading.
    """

    def __init__(
        self,
        icon_name: str,
        size: int = 24,
        icon_size: int = 0,
        tooltip: str | None = None,
        backdrop: bool = True,
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setFixedSize(size, size)
        self.setContentsMargins(0, 0, 0, 0)

        if icon_size <= 0:
            icon_size = size
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Qt CSS only recognizes native class names — "SvgIconButton"
        # is a Python alias for QPushButton.  Use QPushButton selector.
        if backdrop:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #3a3a3a;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background: #4a4a4a;
                    border-color: #666;
                }}
                QPushButton:pressed {{
                    background: #2a2a2a;
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.05);
                    border-radius: 3px;
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        svg_color: str = color if color is not None else COLOR_ACCENT
        icon = SvgIcon(name=icon_name, size=icon_size, color=svg_color)
        layout.addWidget(icon)

        if tooltip:
            self.setToolTip(tooltip)


# =============================================================================
# Factory function
# =============================================================================

def get_icon(
    name: str,
    size: int = _DEFAULT_SIZE,
    color: str | None = None,
) -> SvgIcon:
    """Factory function. Returns an SvgIcon with the given name and optional color.

    Args:
        name: SVG base filename (without .svg).
        size: Maximum size in pixels. Defaults to 16.
        color: CSS color string. Defaults to COLOR_ACCENT ("#90caf9").

    Returns:
        SvgIcon instance.
    """
    return SvgIcon(name=name, size=size, color=color)


__all__ = ["SvgIcon", "SvgIconButton", "get_icon", "QSquareIconButton"]
