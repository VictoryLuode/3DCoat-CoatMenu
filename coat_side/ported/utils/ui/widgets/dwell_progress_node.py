"""
DwellProgressNode - Reusable paint helper for "hover-to-confirm" circular nodes.

A node that visually fills from center outward as the user dwells over it.
When the inner fill reaches the outer edge, the action is invoked. The fill
animation is driven externally by the caller's dwell timer (start time + duration),
so the visual progress always tracks the actual timer 1:1.

This is NOT a QWidget — it's a stateless paint helper invoked from a parent
widget's paintEvent. This keeps it lightweight and avoids extra Qt overhead
for what is fundamentally just a circle with an animated inner disk.

Used by RadialMenuWidget for both branch nodes (open submenu) and exit nodes
(close submenu) so the visual + hover geometry are guaranteed identical.
"""

from __future__ import annotations
from dataclasses import dataclass

try:
    from PySide6.QtCore import Qt, QPointF, QRectF
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
    HAS_QT = True
except ImportError:
    HAS_QT = False


# =============================================================================
# CONSTANTS
# =============================================================================

# Inner fill starts at this fraction of the outer radius (so it's visible
# from the start rather than appearing as a single pixel).
DWELL_FILL_MIN_FRACTION: float = 0.15

# When dwell completes, the fill briefly overshoots/flashes for confirmation.
# This is just a visual hint that the action fired.
DWELL_FLASH_FRACTION: float = 1.10

# Inner fill alpha (0-255) — semi-transparent so the icon/dot stays readable.
DWELL_FILL_ALPHA: int = 160


# =============================================================================
# RENDERER
# =============================================================================


@dataclass
class DwellProgressNode:
    """
    Stateless paint helper for a circular dwell-to-confirm node.

    Call paint() from your parent widget's paintEvent. The node is drawn at
    the given center with the given outer radius. If progress > 0, an inner
    disk grows from center outward, reaching the outer edge at progress=1.0.

    Attributes:
        outer_radius: Radius of the outer circle in pixels.
        border_color: Color of the outer ring (idle).
        border_color_active: Color of the outer ring while highlighted/dwelling.
        bg_color: Background fill color of the outer circle.
        fill_color: Color of the inner dwell-progress disk.
        icon_color: Color of icon/dot (idle).
        icon_color_active: Color of icon/dot while highlighted/dwelling.
        border_width: Idle border stroke width.
        border_width_active: Active border stroke width.
    """

    outer_radius: float = 20.0
    border_color: str = "#555555"
    border_color_active: str = "#90caf9"
    bg_color: str = "#2b2b2b"
    fill_color: str = "#90caf9"
    icon_color: str = "#888888"
    icon_color_active: str = "#90caf9"
    border_width: float = 2.0
    border_width_active: float = 3.0

    if HAS_QT:
        def paint(
            self,
            painter: 'QPainter',
            center: 'QPointF',
            progress: float = 0.0,
            highlighted: bool = False,
            scale: float = 1.0,
            icon: str | None = None,
            icon_font: 'QFont | None' = None,
            center_dot_radius: float = 0.0,
        ) -> None:
            """
            Paint the dwell node.

            Args:
                painter: Active QPainter (parent widget supplies).
                center: Node center in widget coordinates.
                progress: Dwell progress 0.0 (idle) → 1.0 (just completed).
                highlighted: True when dwelling/hovered (active appearance).
                scale: Multiplier on outer_radius for animation effects.
                icon: Optional icon glyph to draw at center.
                icon_font: Font used for the icon (caller-supplied).
                center_dot_radius: If > 0 and no icon, draw a center dot
                    (used for branch nodes without an icon).
            """
            r: float = self.outer_radius * scale

            # ---- Outer ring + background -----------------------------------
            if highlighted:
                pen = QPen(QColor(self.border_color_active),
                           self.border_width_active)
            else:
                pen = QPen(QColor(self.border_color), self.border_width)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(self.bg_color)))
            painter.drawEllipse(center, r, r)

            # ---- Inner dwell-progress disk ---------------------------------
            # Clamp + map to fraction of outer radius. Below MIN_FRACTION the
            # disk would be invisibly small, so we lerp from MIN_FRACTION → 1.0.
            p: float = max(0.0, min(1.0, progress))
            if p > 0.0:
                fill_frac: float = (
                    DWELL_FILL_MIN_FRACTION
                    + (1.0 - DWELL_FILL_MIN_FRACTION) * p
                )
                # Tiny overshoot flash near completion for visual confirmation.
                if p >= 1.0:
                    fill_frac = DWELL_FLASH_FRACTION
                fill_r: float = r * fill_frac

                fill_qcolor = QColor(self.fill_color)
                fill_qcolor.setAlpha(DWELL_FILL_ALPHA)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(fill_qcolor))
                painter.drawEllipse(center, fill_r, fill_r)

            # ---- Icon or center dot ----------------------------------------
            if icon:
                if icon_font is not None:
                    painter.setFont(icon_font)
                painter.setPen(
                    QColor(self.icon_color_active if highlighted
                           else self.icon_color))
                rect = QRectF(center.x() - r, center.y() - r, r * 2, r * 2)
                painter.drawText(rect, Qt.AlignCenter, icon)
            elif center_dot_radius > 0:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(
                    self.icon_color_active if highlighted else self.icon_color
                )))
                painter.drawEllipse(
                    center, center_dot_radius, center_dot_radius)
