"""
Radial menu widget - Phase 1: Simple radial menu.

A direction-based menu that appears at cursor position. Users move mouse
in a direction to select an action, then release trigger key to invoke.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import math

try:
    from PySide6.QtCore import Qt, QPoint, QPointF, Signal, QTimer, QRectF, QEasingCurve, QPropertyAnimation
    from PySide6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QPainterPath, QRadialGradient, QPixmap
    from PySide6.QtSvg import QSvgRenderer
    HAS_QT = True
except ImportError:
    HAS_QT = False

from .dwell_progress_node import DwellProgressNode

# Try to import colors from LKS styles
try:
    from ported.utils.ui.styles import (
        COLOR_BG_PRIMARY,
        COLOR_BG_SECONDARY,
        COLOR_TEXT_PRIMARY,
        COLOR_TEXT_MUTED,
        COLOR_ACCENT,
        COLOR_BORDER,
    )
except ImportError:
    # Fallback colors if styles module not available
    COLOR_BG_PRIMARY = "#2b2b2b"
    COLOR_BG_SECONDARY = "#1e1e1e"
    COLOR_TEXT_PRIMARY = "#e0e0e0"
    COLOR_TEXT_MUTED = "#888888"
    COLOR_ACCENT = "#90caf9"
    COLOR_BORDER = "#555555"

# =============================================================================
# CONSTANTS
# =============================================================================

# Debug mode - show pizza slice highlighting (default: False)
DEBUG_PIZZA_SLICE: bool = False

# Pixels - no selection within this radius (~50% to nodes)
DEAD_ZONE_RADIUS: int = 75
MENU_RADIUS: int = 150              # Pixels - distance from anchor to item centers
# Milliseconds - dwell time before submenu entry/exit
BRANCH_DWELL_MS: int = 250
HIGHLIGHT_SCALE: float = 1.15       # Scale factor for highlighted nodes
# Pixels - extra margin around menu radius for widget size
MENU_WIDGET_MARGIN: int = 100

# Auto-radius and concentric ring layout
MAX_RADIUS: int = 400           # Pixels - max auto-expanded radius before splitting
RING_GAP: int = 80              # Pixels - gap between concentric rings
INTER_ITEM_PAD: int = 20        # Pixels - extra gap between adjacent squircles

# List panel constants
LIST_BUTTON_HEIGHT: int = 24
LIST_BUTTON_PAD: int = 4
LIST_HEADER_HEIGHT: int = 20
LIST_PANEL_PAD_X: int = 8
LIST_PANEL_PAD_Y: int = 8
LIST_PANEL_GAP: int = 16  # gap between ring edge and list panel edge
LIST_PANEL_MIN_WIDTH: int = 120

# Milliseconds - allow very fast flicks to settle after show if the key was
# already released before the popup fully appeared.
FLICK_CONFIRM_TIMEOUT_MS: float = 120.0

# ---- Branch / Exit node geometry (UNIFIED) ----------------------------------
# Branch nodes (open submenu) and exit nodes (close submenu) share identical
# circle geometry so their visual + hover regions can never drift. This avoids
# back-and-forth bouncing when a user grazes the boundary of one but not the
# other during submenu transitions.
BRANCH_NODE_RADIUS: int = 20        # Visible circle radius for both
EXIT_NODE_RADIUS: int = BRANCH_NODE_RADIUS  # Alias kept for readability
# Hover detection radius == visible radius (guaranteed equal).
BRANCH_HOVER_RADIUS: int = BRANCH_NODE_RADIUS
# Hysteresis margin: once a node is the active hover target, the cursor must
# move BRANCH_HOVER_HYSTERESIS_PX past the visible edge before hover is lost.
# Prevents flicker / repeated dwell timer restarts at the boundary.
BRANCH_HOVER_HYSTERESIS_PX: int = 6

# Spawn-item exit buffer: when a menu opens with the cursor already over a
# branch/exit node (e.g. the exit node right after entering a submenu),
# dwell on that node is suppressed until the cursor moves at least this
# many pixels past its outer edge. Prevents micro-jitter from bouncing the
# user back out of a submenu they just entered.
SPAWN_EXIT_BUFFER_PX: int = 18

# No-repeat fallback (ms): if this long after show_at() we still haven't
# received ANY key event (no keyPress, no keyRelease, no auto-repeat),
# assume the key was tapped and released before the OS repeat delay.
# OS repeat delay is typically 250-500ms; 600ms gives generous margin.
NO_REPEAT_RELEASE_MS: float = 600.0

EXIT_ICON_FONT_SIZE: int = 7        # Font size for exit icon (✕)
BRANCH_DOT_RADIUS: int = 3          # Pixels - center dot size
BRANCH_LABEL_OFFSET: int = 25       # Pixels - distance of label above circle
BRANCH_LABEL_FONT_SIZE: int = 9     # Font size for branch label

# Animation settings
ANIM_DURATION_MS: float = 150.0     # Total animation duration (ms)
ANIM_STAGGER_MS: float = 20.0      # Delay between each item (ms) — for fade stagger only

# Highlight animation
HIGHLIGHT_ANIM_MS: float = 100.0    # Duration for highlight transitions
# Extra scale for highlighted (on top of HIGHLIGHT_SCALE)
HIGHLIGHT_SCALE_BONUS: float = 0.05

# Branch transition animation
BRANCH_FADE_OUT_MS: float = 80.0    # Fade out old items when entering branch
BRANCH_FADE_IN_MS: float = 100.0    # Fade in new items when entering branch

# Node appearance (leaf/invoker nodes only)
NODE_PADDING_X: int = 12            # Horizontal padding in squircles
NODE_PADDING_Y: int = 6             # Vertical padding in squircles
NODE_CORNER_RADIUS: int = 8         # Corner radius for squircles
NODE_FONT_SIZE: int = 9             # Normal node font size
NODE_FONT_SIZE_HIGHLIGHT: int = 10  # Highlighted node font size

# Icon rendering in leaf nodes and list buttons
ICON_AREA_SIZE: int = 16           # Fixed square px for SVG/emoji icons
ICON_TEXT_GAP: int = 8             # Gap between icon area and label text

# Directory containing SVG icons
_ICONS_DIR: Path = Path(__file__).resolve().parent.parent / "data"

# Cache for rendered SVG pixmaps: key = "filename|color" → QPixmap
_svg_pixmap_cache: dict[str, "QPixmap"] = {}


def _is_svg_icon(icon_str: str | None) -> bool:
    """Return True if *icon_str* is an SVG filename (case-insensitive)."""
    return bool(icon_str and icon_str.lower().endswith(".svg"))


def _pixmap_for_icon(icon_str: str, color: str) -> "QPixmap | None":
    """Return a cached QPixmap for an SVG icon, or None if not an SVG/file not found."""
    if not _is_svg_icon(icon_str):
        return None
    if not HAS_QT:
        return None
    cache_key: str = f"{icon_str}|{color}"
    cached = _svg_pixmap_cache.get(cache_key)
    if cached is not None:
        return cached
    svg_path: Path = _ICONS_DIR / icon_str
    if not svg_path.is_file():
        return None
    try:
        content: str = svg_path.read_text(encoding="utf-8")
        content = content.replace("currentColor", color)
        renderer: QSvgRenderer = QSvgRenderer(content.encode("utf-8"))
        pixmap: QPixmap = QPixmap(ICON_AREA_SIZE, ICON_AREA_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter: QPainter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        _svg_pixmap_cache[cache_key] = pixmap
        return pixmap
    except Exception:
        return None


def _icon_width_contribution(icon_str: str | None) -> float:
    """Return the extra width (beyond label) that an icon adds.

    SVG icons: ICON_AREA_SIZE + ICON_TEXT_GAP.
    Emoji/text icons: measured text width + ICON_TEXT_GAP.
    No icon: 0.
    """
    if not icon_str:
        return 0.0
    if _is_svg_icon(icon_str):
        return float(ICON_AREA_SIZE + ICON_TEXT_GAP)
    # Emoji / text icon: measure it
    font: QFont = QFont("Segoe UI Emoji", ICON_AREA_SIZE)
    metrics: QFontMetrics = QFontMetrics(font)
    return float(metrics.horizontalAdvance(icon_str) + ICON_TEXT_GAP)


def _draw_icon(
    painter: "QPainter",
    icon_str: str,
    rect: "QRectF",
    color: str,
) -> None:
    """Draw an SVG pixmap or emoji text inside *rect*.

    SVG icons are rendered centred in the rect.  Emoji / text icons are
    drawn with Qt.AlignCenter so they fill the same visual footprint.
    Does NOT modify the painter's font on return (saves/restores state).
    """
    if not icon_str:
        return
    if icon_str.endswith(".svg"):
        pixmap = _pixmap_for_icon(icon_str, color)
        if pixmap is not None:
            x: float = rect.x() + (rect.width() - pixmap.width()) / 2.0
            y: float = rect.y() + (rect.height() - pixmap.height()) / 2.0
            painter.drawPixmap(int(x), int(y), pixmap)
        return
    # Emoji / text icon — save state so the large emoji font doesn't leak
    painter.save()
    font: QFont = QFont("Segoe UI Emoji", ICON_AREA_SIZE)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(rect, Qt.AlignCenter, icon_str)
    painter.restore()


def _draw_label_pill_gradient(
    painter: "QPainter",
    rect: "QRectF",
) -> None:
    """Draw a soft pill-shaped radial gradient behind a label.

    Fades from 40% opacity black at center to fully transparent at edges,
    using a wide smooth falloff so the fade-out happens gently behind the text.
    """
    cx: float = rect.x() + rect.width() / 2.0
    cy: float = rect.y() + rect.height() / 2.0
    # Gradient radius extends well past the rect for a gentle fade
    grad_radius: float = max(rect.width(), rect.height()) * 1.6
    gradient: QRadialGradient = QRadialGradient(cx, cy, grad_radius)
    gradient.setColorAt(0.0, QColor(0, 0, 0, 102))   # 40% black
    gradient.setColorAt(0.30, QColor(0, 0, 0, 60))
    gradient.setColorAt(0.55, QColor(0, 0, 0, 20))
    gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.save()
    painter.setCompositionMode(QPainter.CompositionMode_Multiply)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(gradient))
    # Draw a pill shape matching the rect
    radius: float = rect.height() / 2.0
    painter.drawRoundedRect(rect, radius, radius)
    painter.restore()


# Text outline for better visibility
TEXT_OUTLINE_WIDTH: float = 2.0     # Width of text outline in pixels
TEXT_OUTLINE_COLOR: str = "#000000"  # Black outline for contrast

# =============================================================================
# DATA MODEL
# =============================================================================


@dataclass
class RadialMenuItem:
    """Single item in a radial menu."""
    label: str
    action: Callable[[], None]
    icon: str | None = None
    children: list[RadialMenuItem] | None = None
    angle: float | None = None  # Optional explicit angle (0° = up, clockwise)
    # True if this is an exit node (requires dwell to activate)
    is_exit: bool = False
    # True if rendered as a button block beside the ring, not on it
    is_list: bool = False
    # "left" or "right" placement for list panel
    list_side: str = "right"

    @property
    def is_branch(self) -> bool:
        """Return True if this node has children AND is not a list container."""
        return not self.is_list and self.children is not None and len(self.children) > 0

    @property
    def is_leaf(self) -> bool:
        """Return True if this node has no children and not an exit or list node."""
        return not self.is_branch and not self.is_exit and not self.is_list


# =============================================================================
# LOGGING HELPER
# =============================================================================

def _log_radial(message: str) -> None:
    """
    Log a radial menu event to both the InvocationLogger (if available)
    and the console for debounce/timing debugging.
    """
    print(f"[RadialMenu] {message}")
    try:
        from ported.utils.invocation_logger import get_invocation_logger
        logger = get_invocation_logger()
        logger.log_debug(f"[RadialMenu] {message}")
    except ImportError:
        pass


# =============================================================================
# GEOMETRY & ANGLE MATH
# =============================================================================

def cursor_to_angle(cursor: QPoint, anchor: QPoint) -> float:
    """
    Convert cursor position to angle in degrees.

    0° = up (12 o'clock), angles increase clockwise.

    Args:
        cursor: Current cursor position
        anchor: Anchor point (menu center)

    Returns:
        Angle in degrees (0-360)
    """
    dx: float = cursor.x() - anchor.x()
    dy: float = cursor.y() - anchor.y()

    # atan2 gives angle from positive X axis, counter-clockwise
    # We want angle from negative Y axis (up), clockwise
    angle_rad = math.atan2(dx, -dy)
    angle_deg = math.degrees(angle_rad)

    # Normalize to 0-360
    if angle_deg < 0:
        angle_deg += 360

    return angle_deg


def calculate_slice_boundaries(leaf_angles: list[float]) -> list[tuple[float, float]]:
    """
    Calculate pizza slice boundaries for each leaf node.

    Boundaries are the bisecting angles between adjacent leaves.

    Args:
        leaf_angles: List of leaf node angles (need not be sorted)

    Returns:
        List of (lower_bound, upper_bound) tuples for each leaf
    """
    if not leaf_angles:
        return []

    n = len(leaf_angles)

    # Special case: single leaf covers full 360°
    if n == 1:
        # Return (0, 360) means all angles match this leaf
        # We use (0, 0) with special handling in angle_in_slice
        return [(0.0, 360.0)]

    # Sort leaves by angle to find adjacent neighbors correctly
    sorted_indices = sorted(range(n), key=lambda i: leaf_angles[i])
    sorted_angles = [leaf_angles[i] for i in sorted_indices]

    boundaries: list[tuple[float, float]] = [None] * n  # Pre-allocate

    for sorted_i in range(n):
        original_i = sorted_indices[sorted_i]
        prev_sorted = (sorted_i - 1) % n
        next_sorted = (sorted_i + 1) % n

        prev_angle = sorted_angles[prev_sorted]
        curr_angle = sorted_angles[sorted_i]
        next_angle = sorted_angles[next_sorted]

        # Calculate bisecting angles
        # Lower bound: midpoint between previous and current
        # Handle wrap-around correctly
        diff_prev = curr_angle - prev_angle
        if diff_prev < 0:
            diff_prev += 360
        lower = prev_angle + diff_prev / 2
        if lower >= 360:
            lower -= 360

        # Upper bound: midpoint between current and next
        diff_next = next_angle - curr_angle
        if diff_next < 0:
            diff_next += 360
        upper = curr_angle + diff_next / 2
        if upper >= 360:
            upper -= 360

        boundaries[original_i] = (lower, upper)

    return boundaries


def angle_in_slice(angle: float, lower: float, upper: float) -> bool:
    """
    Check if angle is within a slice boundary.

    Handles wrap-around at 0°/360°.

    Args:
        angle: Angle to test (0-360)
        lower: Lower boundary of slice
        upper: Upper boundary of slice

    Returns:
        True if angle is in slice
    """
    # Normalize all angles to 0-360
    angle = angle % 360
    lower = lower % 360
    upper = upper % 360

    # Special case: full circle (single leaf)
    if lower == 0 and upper == 0:
        return True  # All angles match

    result = False
    if lower < upper:
        # Normal case: no wrap-around
        result = lower <= angle < upper
    elif lower > upper:
        # Wrap-around case: slice crosses 0°
        result = angle >= lower or angle < upper
    else:
        # lower == upper: degenerate case, should not happen with proper calculation
        result = False

    return result


def get_highlighted_leaf(
    cursor: QPoint,
    anchor: QPoint,
    leaf_angles: list[float],
    slice_boundaries: list[tuple[float, float]],
) -> int | None:
    """
    Get index of highlighted leaf based on cursor position.

    Returns None if cursor is in dead zone or no match.

    Args:
        cursor: Current cursor position
        anchor: Menu anchor point
        leaf_angles: Angles of leaf nodes (sorted)
        slice_boundaries: Slice boundaries for each leaf

    Returns:
        Index of highlighted leaf, or None
    """
    # Check dead zone
    dx = cursor.x() - anchor.x()
    dy = cursor.y() - anchor.y()
    distance = math.sqrt(dx * dx + dy * dy)

    if distance < DEAD_ZONE_RADIUS:
        return None

    # Get cursor angle
    cursor_angle = cursor_to_angle(cursor, anchor)

    # Cursor direction vector (normalized)
    cursor_dx = dx / distance
    cursor_dy = dy / distance

    # Find which slice contains cursor
    for i, (lower, upper) in enumerate(slice_boundaries):
        if angle_in_slice(cursor_angle, lower, upper):
            # Additional check: reject if item is >90° away from cursor (dot product < 0)
            # Item direction vector at its angle
            item_angle = leaf_angles[i]
            item_angle_rad = math.radians(item_angle)
            # Convert to our coordinate system (0° = up, clockwise)
            item_dx = math.sin(item_angle_rad)
            item_dy = -math.cos(item_angle_rad)

            # Dot product: reject if negative (>90° away)
            dot = cursor_dx * item_dx + cursor_dy * item_dy
            if dot >= 0:
                return i

    return None


def _angular_distance(a: float, b: float) -> float:
    """Smallest distance in degrees between two angles on a circle."""
    diff: float = abs((a % 360.0) - (b % 360.0)) % 360.0
    return min(diff, 360.0 - diff)


def distribute_node_angles(nodes: list[RadialMenuItem]) -> list[float]:
    """
    Assign angles to nodes: use explicit if specified, else even circle slots.

    Auto mode uses even subdivisions of 360° (N items → step ``360/N``),
    starting at 0° (up) and proceeding clockwise in list order.

    When some angles are explicit, auto nodes claim the remaining even slots
    (nearest unused slot is reserved by each explicit angle) so they do not
    stack on top of locked positions.

    Args:
        nodes: List of menu items that occupy pie slots

    Returns:
        List of angles (one per node)
    """
    n: int = len(nodes)
    if n == 0:
        return []

    angle_step: float = 360.0 / n
    slot_angles: list[float] = [i * angle_step for i in range(n)]

    # All-explicit: keep author values as-is.
    if all(node.angle is not None for node in nodes):
        return [float(node.angle) % 360.0 for node in nodes]  # type: ignore[arg-type]

    # All-auto: even subdivisions in list order (canonical auto layout).
    if all(node.angle is None for node in nodes):
        return list(slot_angles)

    # Mixed: reserve slots nearest to each explicit angle, fill the rest.
    result: list[float | None] = [None] * n
    used_slots: set[int] = set()
    for i, node in enumerate(nodes):
        if node.angle is None:
            continue
        explicit: float = float(node.angle) % 360.0
        result[i] = explicit
        nearest: int = min(
            range(n),
            key=lambda s: _angular_distance(slot_angles[s], explicit),
        )
        used_slots.add(nearest)

    free_slots: list[int] = [s for s in range(n) if s not in used_slots]
    free_i: int = 0
    for i, node in enumerate(nodes):
        if result[i] is not None:
            continue
        if free_i < len(free_slots):
            result[i] = slot_angles[free_slots[free_i]]
            free_i += 1
        else:
            result[i] = slot_angles[i]

    return [float(a) for a in result]


def assign_circle_node_angles(items: list[RadialMenuItem]) -> list[float]:
    """Assign pie angles for a full menu item list.

    Branches and leaf actions share one even circle subdivision so they never
    land on the same auto slot. List panels (off-ring) and exit nodes (center)
    do not consume slots.
    """
    angles: list[float] = [0.0] * len(items)
    circle_indices: list[int] = []
    circle_items: list[RadialMenuItem] = []
    for i, item in enumerate(items):
        if item.is_list or item.is_exit:
            continue
        circle_indices.append(i)
        circle_items.append(item)
    for idx, angle in zip(circle_indices, distribute_node_angles(circle_items)):
        angles[idx] = angle
    return angles


def get_node_position(angle: float, radius: float, center: QPointF) -> QPointF:
    """
    Convert angle + radius to screen position relative to center.

    Args:
        angle: Angle in degrees (0° = up, clockwise)
        radius: Distance from center
        center: Center point

    Returns:
        Position as QPointF
    """
    # Convert to radians, adjust for Qt coordinate system
    angle_rad = math.radians(angle)

    # Calculate position (remember: 0° is up, clockwise)
    x = center.x() + radius * math.sin(angle_rad)
    y = center.y() - radius * math.cos(angle_rad)

    return QPointF(x, y)


def draw_text_with_outline(
    painter: 'QPainter',
    rect: 'QRectF',
    alignment: 'Qt.AlignmentFlag',
    text: str,
    text_color: str,
    outline_color: str = TEXT_OUTLINE_COLOR,
    outline_width: float = TEXT_OUTLINE_WIDTH,
) -> None:
    """
    Draw text with an outline for better visibility on any background.

    Args:
        painter: QPainter instance
        rect: Rectangle to draw text in
        alignment: Text alignment flags
        text: Text string to draw
        text_color: Color for the text
        outline_color: Color for the outline (default: black)
        outline_width: Width of the outline in pixels
    """
    # Save current painter state
    painter.save()

    # Get font metrics for accurate positioning
    font = painter.font()
    metrics = painter.fontMetrics()

    # Calculate text position based on alignment
    # addText() uses baseline positioning, so we need to calculate carefully
    text_width = metrics.horizontalAdvance(text)
    text_height = metrics.height()
    ascent = metrics.ascent()

    # Calculate X position
    if alignment & Qt.AlignHCenter:
        x = rect.center().x() - text_width / 2
    elif alignment & Qt.AlignRight:
        x = rect.right() - text_width
    else:  # AlignLeft
        x = rect.left()

    # Calculate Y position (baseline, not top)
    if alignment & Qt.AlignVCenter:
        # Center vertically: middle of rect, adjust for text metrics
        y = rect.center().y() + ascent / 2 - metrics.descent()
    elif alignment & Qt.AlignBottom:
        y = rect.bottom() - metrics.descent()
    else:  # AlignTop
        y = rect.top() + ascent

    # Create a path from the text at the calculated position
    path = QPainterPath()
    path.addText(x, y, font, text)

    # Draw outline
    painter.setPen(QPen(QColor(outline_color), outline_width, Qt.SolidLine,
                        Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

    # Draw text fill
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(text_color)))
    painter.drawPath(path)

    # Restore painter state
    painter.restore()


# =============================================================================
# RING LAYOUT COMPUTATION
# =============================================================================


def compute_ring_layout(items: list[RadialMenuItem]) -> list[tuple[float, int]]:
    """
    Distribute items into one or more concentric rings to prevent overlap.

    Each ring holds a subset of items placed evenly around its own circle.
    Returns a list of (radius, item_count) tuples, from innermost to outermost.

    Strategy:
    1. Measure the widest label using QFont with NODE_FONT_SIZE
    2. Compute R_min for all items on a single ring
    3. If R_min <= MAX_RADIUS, single ring
    4. Otherwise, find how many items fit at MAX_RADIUS and split evenly
    """
    n: int = len(items)
    if n == 0:
        return []

    font: QFont = QFont("Arial", NODE_FONT_SIZE)

    fm = QFontMetrics(font)

    # Measure the widest label across all items
    max_width: float = 0.0
    for item in items:
        text: str = item.label
        width: float = fm.horizontalAdvance(text) + _icon_width_contribution(item.icon) + NODE_PADDING_X * 2
        if width > max_width:
            max_width = width

    # Compute minimum radius for all items on a single ring
    # chord = 2*R*sin(pi/N), need chord >= max_width + INTER_ITEM_PAD
    # R_min = (max_width + INTER_ITEM_PAD) / (2 * sin(pi/N))
    sin_half_angle: float = math.sin(math.pi / n)
    if sin_half_angle < 0.0001:
        # Degenerate case: very few items, just use MENU_RADIUS
        return [(float(MENU_RADIUS), n)]

    r_min: float = (max_width + INTER_ITEM_PAD) / (2.0 * sin_half_angle)

    # Single ring case
    if r_min <= MAX_RADIUS:
        # Use max of r_min and MENU_RADIUS (never shrink below default)
        radius: float = max(r_min, float(MENU_RADIUS))
        return [(radius, n)]

    # Multi-ring case: find max items that fit at MAX_RADIUS
    # Solve for n_fit: (max_width + INTER_ITEM_PAD) / (2 * sin(pi/n_fit)) <= MAX_RADIUS
    # sin(pi/n_fit) >= (max_width + INTER_ITEM_PAD) / (2 * MAX_RADIUS)
    min_sin: float = (max_width + INTER_ITEM_PAD) / (2.0 * MAX_RADIUS)
    if min_sin >= 1.0:
        # Even 2 items don't fit at MAX_RADIUS (extremely wide labels)
        items_per_ring: int = max(2, n)
    else:
        n_fit: int = int(math.pi / math.asin(min_sin))
        # n_fit is the max items per ring without overlap at MAX_RADIUS
        items_per_ring = max(2, n_fit)

    # Split evenly: each ring gets ~items_per_ring items
    num_rings: int = max(1, int(math.ceil(n / items_per_ring)))
    items_per_ring = max(2, int(math.ceil(n / num_rings)))

    # Build ring list: inner ring at MENU_RADIUS, each subsequent +RING_GAP
    rings: list[tuple[float, int]] = []
    remaining: int = n
    for ring_idx in range(num_rings):
        ring_radius: float = float(MENU_RADIUS) + ring_idx * RING_GAP
        ring_count: int = min(items_per_ring, remaining)
        if ring_count > 0:
            rings.append((ring_radius, ring_count))
            remaining -= ring_count

    return rings


def resolve_ring_overlaps(
    ring_radii: list[float],
    ring_item_indices: list[list[int]],
    items: list[RadialMenuItem],
    node_angles: list[float],
    max_radius: int = MAX_RADIUS * 2,
) -> list[float]:
    """
    Expand ring radii until no adjacent squircle rects overlap.

    For each ring, compute the bounding rect of each leaf item at its angle
    and radius. Adjacent items (angularly sorted) are checked for overlap.
    If overlap is found, the ring radius is incremented and re-checked.

    Pairs where **both** items have an explicit (manual) angle are skipped —
    close manual placements are accepted as author intent; expanding the ring
    to separate 1°/2° neighbors would explode the pie radius.

    Args:
        ring_radii: Initial radii for each ring
        ring_item_indices: Item indices belonging to each ring
        items: All RadialMenuItems (to measure label widths)
        node_angles: Angles for each item in items
        max_radius: Hard cap on ring expansion

    Returns:
        Adjusted ring radii (may be larger than input)
    """
    font: QFont = QFont("Arial", NODE_FONT_SIZE)
    font_hl: QFont = QFont("Arial", NODE_FONT_SIZE_HIGHLIGHT, QFont.Bold)
    metrics: QFontMetrics = QFontMetrics(font)
    metrics_hl: QFontMetrics = QFontMetrics(font_hl)

    item_widths: list[float] = []
    item_heights: list[float] = []
    for item in items:
        if item.is_leaf:
            icon_w: float = _icon_width_contribution(item.icon)
            w: float = max(
                metrics.horizontalAdvance(item.label),
                metrics_hl.horizontalAdvance(item.label),
            ) + icon_w
            w += NODE_PADDING_X * 2
            h: float = max(metrics.height(), metrics_hl.height()) + NODE_PADDING_Y * 2
            item_widths.append(w)
            item_heights.append(h)
        else:
            item_widths.append(0.0)
            item_heights.append(0.0)

    adjusted_radii: list[float] = list(ring_radii)

    for ring_idx, indices in enumerate(ring_item_indices):
        if len(indices) <= 1:
            continue

        sorted_indices: list[int] = sorted(indices, key=lambda i: node_angles[i] % 360)
        n: int = len(sorted_indices)
        radius: float = adjusted_radii[ring_idx]

        for _ in range(200):
            has_overlap: bool = False
            for j in range(n):
                idx_a: int = sorted_indices[j]
                idx_b: int = sorted_indices[(j + 1) % n]

                # Both angles locked by the author — do not inflate radius.
                if (
                    items[idx_a].angle is not None
                    and items[idx_b].angle is not None
                ):
                    continue

                angle_a: float = math.radians(node_angles[idx_a])
                angle_b: float = math.radians(node_angles[idx_b])

                x_a: float = radius * math.sin(angle_a)
                y_a: float = -radius * math.cos(angle_a)
                x_b: float = radius * math.sin(angle_b)
                y_b: float = -radius * math.cos(angle_b)

                wa: float = item_widths[idx_a]
                ha: float = item_heights[idx_a]
                wb: float = item_widths[idx_b]
                hb: float = item_heights[idx_b]

                rect_a: QRectF = QRectF(x_a - wa / 2, y_a - ha / 2, wa, ha)
                rect_b: QRectF = QRectF(x_b - wb / 2, y_b - hb / 2, wb, hb)

                if rect_a.intersects(rect_b):
                    has_overlap = True
                    break

            if not has_overlap:
                break

            radius += 2

            if radius > max_radius:
                break

        adjusted_radii[ring_idx] = radius

    return adjusted_radii


# =============================================================================
# RADIAL MENU WIDGET
# =============================================================================

if HAS_QT:
    class RadialMenuWidget(QWidget):
        """
        Frameless overlay widget displaying radial menu sectors.

        UX Pattern:
        1. Hold trigger key → menu appears at cursor
        2. Move mouse in direction → sector highlights
        3. Release trigger key → highlighted action invokes
        """

        # Signals
        # Emitted when highlighted sector changes
        highlightChanged = Signal(int)

        def __init__(self, parent=None):
            super().__init__(parent)

            # Window flags for overlay
            self.setWindowFlags(
                Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)

            # CRITICAL: Make widget receive mouse events even in transparent areas
            # Without this, Qt only sends events when mouse is over painted pixels
            self.setAttribute(Qt.WA_TransparentForMouseEvents,
                              False)  # Explicitly disable
            # Alternative to setMouseTracking
            self.setAttribute(Qt.WA_MouseTracking, True)

            # State
            self._items: list[RadialMenuItem] = []
            self._anchor: QPoint | None = None
            self._highlighted_leaf_index: int | None = None

            # Phase 2: Tree navigation state
            # Navigation breadcrumb
            self._menu_stack: list[list[RadialMenuItem]] = []
            # Anchor positions for each level
            self._anchor_stack: list[QPoint] = []
            self._hovered_branch_item: RadialMenuItem | None = None
            self._dwell_timer: QTimer = QTimer(self)
            self._dwell_timer.setSingleShot(True)
            self._dwell_timer.timeout.connect(self._on_dwell_timeout)
            # Timestamp (monotonic seconds) when the current dwell started.
            # 0.0 means no dwell in progress. Used to drive the dwell-fill
            # animation in paint() so the visual progress maps 1:1 to the
            # actual timer.
            self._dwell_start_time: float = 0.0

            # Hover debounce: track if cursor spawned on top of a node
            self._cursor_has_left_spawn_item: bool = True  # Start True for root menu
            # The specific item the cursor was sitting on when this menu
            # appeared (e.g. the new exit node after entering a submenu).
            # Dwell on this item is blocked until the cursor moves a
            # generous distance away from it — preventing the auto-bounce
            # back into the parent menu when the user is just holding
            # still over the branch they intentionally entered.
            self._spawn_item: RadialMenuItem | None = None
            # Track label of branch we exited from
            self._just_exited_from_label: str | None = None

            # Key release tracking
            self._keys_currently_pressed: set[int] = set()
            self._trigger_keycode: int | None = None  # Qt keycode for the trigger key
            self._trigger_vk: int | None = None       # Win32 virtual-key for polling
            self._show_time: float = 0.0
            self._flick_mode: bool = False
            self._flick_deadline: float = 0.0

            # Cursor tracking for drawing live cursor line
            self._last_cursor_widget_pos: QPointF | None = None

            # Timer for polling cursor position (backup when mouseMoveEvent not firing)
            self._cursor_poll_timer: QTimer = QTimer(self)
            self._cursor_poll_timer.setInterval(16)  # ~60fps
            self._cursor_poll_timer.timeout.connect(self._poll_cursor)

            # Geometry cache
            self._leaf_angles: list[float] = []
            self._slice_boundaries: list[tuple[float, float]] = []
            self._node_angles: list[float] = []
            self._node_radii: list[float] = []  # radius for each item (MENU_RADIUS or ring radius)

            # Ring layout state (auto-radius + concentric rings)
            self._ring_radii: list[float] = []  # radius of each ring
            self._ring_item_indices: list[list[int]] = []  # item indices per ring
            self._ring_flat_leaf_to_item: list[int] = []  # flat leaf index -> item index
            self._ring_slice_boundaries: list[list[tuple[float, float]]] = []  # per-ring slice boundaries

            # Center label state
            self._menu_name: str = ""
            self._menu_name_stack: list[str] = []  # push/pop with enter/exit submenu

            # List panel geometry state
            self._list_button_rects: list[list[QRectF]] = []   # per-list: button bounding rects
            self._list_panel_rects: list[QRectF] = []            # per-list: full panel bounding rect
            self._list_flat_leaf_to_item: dict[int, int] = {}    # highlighted_list_index -> items index

            # List panel highlight state
            self._highlighted_list_container: int | None = None
            self._highlighted_list_button: int | None = None

            # Shared paint helper for branch + exit nodes. Using one renderer
            # instance for both guarantees identical visual geometry.
            self._dwell_node_renderer: DwellProgressNode = DwellProgressNode(
                outer_radius=float(BRANCH_NODE_RADIUS),
                border_color=COLOR_BORDER,
                border_color_active=COLOR_ACCENT,
                bg_color=COLOR_BG_PRIMARY,
                fill_color=COLOR_ACCENT,
                icon_color=COLOR_TEXT_MUTED,
                icon_color_active=COLOR_ACCENT,
            )

            # Animation state
            self._anim_start_time: float = 0.0  # Timestamp when animation started
            self._anim_active: bool = False      # Is animation currently running

            # Animation objects (kept alive as member variables to prevent GC)
            self._show_fade_anim: QPropertyAnimation | None = None
            self._hide_fade_anim: QPropertyAnimation | None = None

            # Highlight animation state
            self._highlight_anim_start: float = 0.0
            self._prev_highlighted_index: int | None = None
            self._highlight_anim_active: bool = False

            # Branch transition animation state
            self._branch_transition_start: float = 0.0
            self._branch_transition_active: bool = False
            # True if exiting, False if entering
            self._branch_transition_exiting: bool = False

            # Fade-out pending action (dispatched after animation completes)
            self._pending_action: Callable[[], None] | None = None

            # Enable mouse tracking
            self.setMouseTracking(True)

        # ---------------------------------------------------------------------
        # Public API
        # ---------------------------------------------------------------------

        def set_items(self, items: list[RadialMenuItem]) -> None:
            """Set menu items to display."""
            self._items = items
            self._highlighted_leaf_index = None
            self._recalculate_geometry()
            self.update()

        def set_geometry_params(
            self,
            dead_zone_radius: int | None = None,
            menu_radius: int | None = None,
            branch_hover_radius: int | None = None,
            branch_dwell_ms: int | None = None,
        ) -> None:
            """
            Update geometry parameters from settings.

            This allows runtime configuration without modifying module constants.
            Note: Parameters update module-level constants which affect all instances.

            Args:
                dead_zone_radius: Dead zone radius in pixels
                menu_radius: Menu radius in pixels
                branch_hover_radius: Branch hover detection radius in pixels
                branch_dwell_ms: Dwell time in milliseconds
            """
            global DEAD_ZONE_RADIUS, MENU_RADIUS, BRANCH_HOVER_RADIUS, BRANCH_DWELL_MS
            global BRANCH_NODE_RADIUS, EXIT_NODE_RADIUS

            if dead_zone_radius is not None:
                DEAD_ZONE_RADIUS = dead_zone_radius
            if menu_radius is not None:
                MENU_RADIUS = menu_radius
            if branch_hover_radius is not None:
                # Keep visual + hover + renderer locked together so they
                # cannot drift and cause hover/visual mismatches.
                BRANCH_HOVER_RADIUS = branch_hover_radius
                BRANCH_NODE_RADIUS = branch_hover_radius
                EXIT_NODE_RADIUS = branch_hover_radius
                if hasattr(self, "_dwell_node_renderer"):
                    self._dwell_node_renderer.outer_radius = float(
                        branch_hover_radius)
            if branch_dwell_ms is not None:
                BRANCH_DWELL_MS = branch_dwell_ms

            # Recalculate geometry with new parameters
            if self._items:
                self._recalculate_geometry()
                self.update()

        def set_trigger_keycode(self, keycode: int | None) -> None:
            """
            Set the Qt keycode of the trigger key used to invoke this menu.

            This allows the widget to specifically wait for the trigger key's
            release before closing, rather than closing on any key release.

            Args:
                keycode: Qt keycode (e.g., Qt.Key_X), or None for fallback behavior
            """
            from ported.utils.win32_key_state import qt_key_to_vk

            self._trigger_keycode = keycode
            self._trigger_vk = qt_key_to_vk(keycode)

        def set_menu_name(self, name: str) -> None:
            """Set the menu name shown in the center label."""
            self._menu_name = name
            self.update()

        def _recalculate_geometry(self) -> None:
            """Recalculate node positions, ring layout, and slice boundaries."""
            if not self._items:
                self._leaf_angles = []
                self._slice_boundaries = []
                self._node_angles = []
                self._node_radii = []
                self._ring_radii = []
                self._ring_item_indices = []
                self._ring_flat_leaf_to_item = []
                self._ring_slice_boundaries = []
                return

            # Branches + leaf actions share one even circle subdivision.
            # Lists / exit nodes do not consume pie slots.
            self._node_angles = assign_circle_node_angles(self._items)
            # Fixed pie radius (set via set_geometry_params / menu config).
            # No auto-expand or multi-ring split — authors raise radius to deoverlap.
            pie_radius: float = float(MENU_RADIUS)
            self._node_radii = [pie_radius] * len(self._items)

            leaf_item_indices: list[int] = [
                i for i, item in enumerate(self._items) if item.is_leaf
            ]

            self._leaf_angles = [
                self._node_angles[i] for i in leaf_item_indices
            ]
            self._ring_radii = [pie_radius] if leaf_item_indices else []
            self._ring_item_indices = (
                [list(leaf_item_indices)] if leaf_item_indices else []
            )

            # Calculate slice boundaries from all leaf angles (flat list)
            self._slice_boundaries = calculate_slice_boundaries(self._leaf_angles)

            # Build flat leaf-to-item-index mapping for highlight resolution
            self._ring_flat_leaf_to_item: list[int] = list(leaf_item_indices)

            # Build per-ring slice boundaries for ring-aware highlight detection
            self._ring_slice_boundaries = []
            if leaf_item_indices:
                self._ring_slice_boundaries.append(
                    calculate_slice_boundaries(self._leaf_angles)
                )

            # ---- List panel layout computation ----
            # Collect list items from self._items
            list_indices: list[int] = [i for i, item in enumerate(self._items) if item.is_list]
            self._list_button_rects = []
            self._list_panel_rects = []
            self._list_flat_leaf_to_item = {}

            if list_indices:
                font: QFont = QFont("Arial", NODE_FONT_SIZE)
                metrics: QFontMetrics = QFontMetrics(font)

                max_radius: float = max(self._ring_radii) if self._ring_radii else float(MENU_RADIUS)

                # Compute the maximum squircle half-width for ring leaf items
                # so list panels are placed outside the actual label bounds,
                # not just outside the ring center.
                max_squircle_half_w: float = 0.0
                for i, item in enumerate(self._items):
                    if not item.is_leaf:
                        continue
                    text: str = item.label
                    tw: int = metrics.horizontalAdvance(text)
                    # Use highlighted font size for worst-case width
                    hl_font: QFont = QFont("Arial", NODE_FONT_SIZE_HIGHLIGHT, QFont.Bold)
                    hl_metrics: QFontMetrics = QFontMetrics(hl_font)
                    tw_hl: int = hl_metrics.horizontalAdvance(text)
                    sw: float = float(max(tw, tw_hl)) + _icon_width_contribution(item.icon) + NODE_PADDING_X * 2
                    max_squircle_half_w = max(max_squircle_half_w, sw / 2.0)

                list_leaf_offset: int = 0

                # --- Pass 1: Collect panel dimensions and button rects ---
                # Stored in list_indices order so output lists stay aligned
                panel_data: list[tuple[int, str, float, float, list[QRectF]]] = []
                # (item_idx, side, panel_width, panel_height, button_rects)

                for item_idx in list_indices:
                    item: RadialMenuItem = self._items[item_idx]
                    if not item.children:
                        continue

                    # Compute panel layout — measure every button's text width
                    # so the panel expands to fit the widest label (incl. icon).
                    # LIST_PANEL_MIN_WIDTH is a floor, never a cap.
                    panel_width: int = LIST_PANEL_MIN_WIDTH
                    for child in item.children:
                        text: str = child.label
                        text_w: float = (
                            metrics.horizontalAdvance(text)
                            + _icon_width_contribution(child.icon)
                            + NODE_PADDING_X * 2
                            + LIST_PANEL_PAD_X * 2
                        )
                        panel_width = max(panel_width, math.ceil(text_w))

                    panel_height: float = float(LIST_HEADER_HEIGHT + LIST_PANEL_PAD_Y +
                                         len(item.children) * (LIST_BUTTON_HEIGHT + LIST_BUTTON_PAD) + LIST_PANEL_PAD_Y)

                    # Compute button rects within panel (relative to panel origin)
                    button_rects: list[QRectF] = []
                    btn_y: float = LIST_HEADER_HEIGHT + LIST_PANEL_PAD_Y
                    for child in item.children:
                        btn_rect: QRectF = QRectF(
                            float(LIST_PANEL_PAD_X), btn_y,
                            float(panel_width - LIST_PANEL_PAD_X * 2), float(LIST_BUTTON_HEIGHT))
                        button_rects.append(btn_rect)
                        btn_y += LIST_BUTTON_HEIGHT + LIST_BUTTON_PAD

                        # Map this list button to a virtual flat leaf index for highlight resolution
                        self._list_flat_leaf_to_item[list_leaf_offset] = item_idx
                        list_leaf_offset += 1

                    side: str = item.list_side if item.list_side == "right" else "left"
                    panel_data.append((item_idx, side, float(panel_width), panel_height, button_rects))

                # --- Pass 2: Compute horizontal positions per side ---
                # Right-side panels: row extending right from the outermost squircle edge
                # Left-side panels: row extending left from the outermost squircle edge
                panel_edge: float = max_radius + max_squircle_half_w + LIST_PANEL_GAP
                right_x: float = panel_edge
                left_x: float = -panel_edge  # right edge of first left panel
                side_x: dict[str, float] = {"right": right_x, "left": left_x}

                for item_idx, side, panel_width, panel_height, button_rects in panel_data:
                    if side == "right":
                        panel_x: float = side_x["right"]
                        side_x["right"] += panel_width + LIST_PANEL_GAP
                    else:
                        panel_x = side_x["left"] - panel_width
                        side_x["left"] -= panel_width + LIST_PANEL_GAP

                    panel_y: float = -panel_height / 2.0
                    self._list_panel_rects.append(QRectF(panel_x, panel_y, panel_width, panel_height))
                    self._list_button_rects.append(button_rects)

        def _compute_widget_size(self) -> int:
            """Return the square widget size needed to contain the current menu.

            Accounts for the outermost ring radius and any left/right list
            panels. Assumes ``_recalculate_geometry()`` has already run for the
            items currently displayed — otherwise the extents are stale.
            """
            effective_radius: int = max(
                MENU_RADIUS,
                int(max(self._ring_radii)) if self._ring_radii else 0,
            )
            # Extend widget horizontally for list panels
            list_right_width: float = 0.0
            list_left_width: float = 0.0
            for panel_rect in self._list_panel_rects:
                if panel_rect.x() > 0:
                    list_right_width = max(
                        list_right_width, panel_rect.x() + panel_rect.width())
                else:
                    list_left_width = max(list_left_width, abs(panel_rect.x()))
            max_extent: float = max(
                float(effective_radius),
                list_right_width + MENU_WIDGET_MARGIN,
                list_left_width + MENU_WIDGET_MARGIN,
            )
            return int((max_extent + MENU_WIDGET_MARGIN) * 2)

        def _resize_and_center_on(self, anchor: QPoint) -> None:
            """Resize widget to fit the current menu and center it on *anchor*.

            MUST be called AFTER ``_recalculate_geometry()`` so ring/panel
            extents reflect the items currently displayed. Calling it before
            recalculation (e.g. during submenu enter/exit) sizes the widget for
            the previous menu and clips the new one.
            """
            size: int = self._compute_widget_size()
            self.setFixedSize(size, size)
            self.move(anchor.x() - size // 2, anchor.y() - size // 2)

        def show_at(self, pos: QPoint) -> None:
            """Show menu centered at given screen position."""
            self._anchor = pos

            # Reset key press state for new menu invocation
            import time as _time
            from ported.utils.win32_key_state import is_vk_down

            # Cancel any in-progress hide fade so a prior dismiss cannot call
            # hide() after we re-show (invisible stuck overlay hazard).
            if self._hide_fade_anim is not None:
                self._hide_fade_anim.stop()
                self._hide_fade_anim = None
            self._pending_action = None

            self._keys_currently_pressed.clear()
            self._show_time = _time.monotonic()
            self._flick_mode = False
            self._flick_deadline = 0.0

            if self._trigger_vk is not None and not is_vk_down(self._trigger_vk):
                self._flick_mode = True
                self._flick_deadline = self._show_time + \
                    (FLICK_CONFIRM_TIMEOUT_MS / 1000.0)

            # Log to invocation logger for debounce debugging
            _log_radial(
                f"show_at: trigger=0x{self._trigger_keycode:04X}, "
                f"flick_mode={self._flick_mode}"
                if self._trigger_keycode else
                f"show_at: trigger=None, flick_mode={self._flick_mode}"
            )

            # Start animation
            self._anim_start_time = self._show_time
            self._anim_active = True

            # Reset branch transition (new menu opened)
            self._branch_transition_active = False

            # Size widget to fully contain the menu geometry and position so the
            # anchor sits at the widget center. Geometry was already recalculated
            # by set_items() before show_at() is called.
            self._resize_and_center_on(pos)

            # Fade-in: use QGraphicsOpacityEffect to prevent first-frame flash
            # Non-item elements (dead zone, center label, background) start invisible
            if not self.graphicsEffect():
                effect: QGraphicsOpacityEffect = QGraphicsOpacityEffect(self)
                effect.setOpacity(0.0)
                self.setGraphicsEffect(effect)
            gfx_effect = self.graphicsEffect()
            gfx_effect.setOpacity(0.0)

            # Kill any prior show animation before starting a new one
            if self._show_fade_anim is not None:
                self._show_fade_anim.stop()
                self._show_fade_anim = None

            self._show_fade_anim = QPropertyAnimation(gfx_effect, b"opacity")
            self._show_fade_anim.setDuration(100)
            self._show_fade_anim.setStartValue(0.0)
            self._show_fade_anim.setEndValue(1.0)
            self._show_fade_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._show_fade_anim.finished.connect(
                lambda: setattr(self, '_show_fade_anim', None)
            )
            self._show_fade_anim.start()

            # Show widget on top, but NEVER activate/steal focus from 3DCoat.
            # WindowStaysOnTopHint already keeps us above 3DCoat's window.
            # activateWindow() would briefly steal keyboard focus, causing
            # 3DCoat to miss the trigger-key release → stuck key state.
            self.show()

            # Start cursor polling timer for smooth cursor line updates
            self._cursor_poll_timer.start()

            # Initialize cursor position and highlight immediately so
            # very fast flicks can resolve before the first poll tick.
            from PySide6.QtGui import QCursor
            cursor_screen = QCursor.pos()
            cursor_widget = self.mapFromGlobal(cursor_screen)
            self._update_cursor_state(cursor_screen, QPointF(cursor_widget))

            self.update()

        def hide_and_invoke(self) -> None:
            """Hide menu with animated fade-out and dispatch selected action."""
            # Stop cursor polling
            self._cursor_poll_timer.stop()

            # Synthesize key-up EARLY so 3DCoat's input state is clean
            # well before the action fires. Firing it right before
            # QTimer.singleShot(0, action) corrupts 3DCoat's internal
            # state and deadlocks $LKS_ command processing.
            self._synth_trigger_key_up()

            # Resolve action to dispatch after fade-out completes
            action_to_dispatch: Callable[[], None] | None = None

            # Invoke action if a leaf is highlighted
            if self._highlighted_leaf_index is not None:
                # Use ring-aware mapping: highlighted leaf index → item in _items
                if (
                    self._ring_flat_leaf_to_item
                    and 0 <= self._highlighted_leaf_index < len(self._ring_flat_leaf_to_item)
                ):
                    item_idx: int = self._ring_flat_leaf_to_item[self._highlighted_leaf_index]
                    if 0 <= item_idx < len(self._items):
                        item = self._items[item_idx]
                        _log_radial(f"invoke leaf: \"{item.label}\"")
                        action_to_dispatch = item.action
                else:
                    # Fallback: flat leaf list (single ring / backward compat)
                    leaf_nodes = [item for item in self._items if item.is_leaf]
                    if 0 <= self._highlighted_leaf_index < len(leaf_nodes):
                        item = leaf_nodes[self._highlighted_leaf_index]
                        _log_radial(f"invoke leaf (fallback): \"{item.label}\"")
                        action_to_dispatch = item.action

            # Invoke list button action if highlighted
            if action_to_dispatch is None and self._highlighted_list_container is not None and self._highlighted_list_button is not None:
                if self._highlighted_list_container < len(self._items):
                    container: RadialMenuItem = self._items[self._highlighted_list_container]
                    if container.is_list and container.children and self._highlighted_list_button < len(container.children):
                        item = container.children[self._highlighted_list_button]
                        _log_radial(f"invoke list button: \"{item.label}\"")
                        action_to_dispatch = item.action

            if action_to_dispatch is None:
                _log_radial("hide (no action highlighted)")

            # Animated fade-out using QGraphicsOpacityEffect
            effect = self.graphicsEffect() or QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)

            # Kill any prior hide animation before starting a new one
            if self._hide_fade_anim is not None:
                self._hide_fade_anim.stop()
                self._hide_fade_anim = None

            self._hide_fade_anim = QPropertyAnimation(effect, b"opacity")
            self._hide_fade_anim.setDuration(80)
            self._hide_fade_anim.setStartValue(1.0)
            self._hide_fade_anim.setEndValue(0.0)
            self._hide_fade_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._hide_fade_anim.finished.connect(self._on_hide_fade_complete)
            self._pending_action = action_to_dispatch
            self._hide_fade_anim.start()

        def dismiss_without_invoke(self) -> None:
            """Immediately hide without invoking, clearing timers/anims/opacity.

            Used by editor hold-to-preview release and other cancel paths.
            Prevents a translucent always-on-top ToolTip from lingering and
            blocking mouse/keyboard to the LKS panel.
            """
            self._cursor_poll_timer.stop()
            self._dwell_timer.stop()
            self._dwell_start_time = 0.0
            self._flick_mode = False
            self._pending_action = None

            if self._hide_fade_anim is not None:
                self._hide_fade_anim.stop()
                self._hide_fade_anim = None
            if self._show_fade_anim is not None:
                self._show_fade_anim.stop()
                self._show_fade_anim = None

            effect = self.graphicsEffect()
            if effect is not None:
                effect.setOpacity(1.0)

            self.set_trigger_keycode(None)
            self.hide()
            _log_radial("dismiss_without_invoke")

        def _synth_trigger_key_up(self) -> None:
            """Send a Win32 key-up for the trigger VK so 3DCoat sees the release.

            Even without grabKeyboard(), 3DCoat may miss the OS-level key-up
            if a Qt focus transition briefly occured during the hide sequence.
            Sending a synthetic key-up guarantees 3DCoat's modifier state
            is clean before the action executes.
            """
            if self._trigger_vk is None:
                return
            from ported.utils.win32_key_state import IS_WINDOWS
            if not IS_WINDOWS:
                return
            try:
                import ctypes
                KEYEVENTF_KEYUP: int = 0x0002
                ctypes.windll.user32.keybd_event(
                    self._trigger_vk, 0, KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

        def _on_hide_fade_complete(self) -> None:
            """Cleanup after hide fade-out animation completes, then dispatch action."""
            self._hide_fade_anim = None
            self._do_hide_and_dispatch()

        def _do_hide_and_dispatch(self) -> None:
            """Called when fade-out animation completes. Hides widget and dispatches pending action."""
            self.hide()
            if self._pending_action is not None:
                action: Callable[[], None] = self._pending_action
                self._pending_action = None
                QTimer.singleShot(0, action)

        # ---------------------------------------------------------------------
        # Phase 2: Tree Navigation Methods
        # ---------------------------------------------------------------------

        def _get_item_widget_pos(self, item: RadialMenuItem) -> QPointF | None:
            """
            Return the widget-coordinate center of ``item`` (or None).

            Exit nodes are at widget center; branches are at MENU_RADIUS
            along their assigned angle.
            """
            center = QPointF(self.width() / 2, self.height() / 2)
            if item.is_exit:
                return center
            try:
                idx = self._items.index(item)
                angle = self._node_angles[idx]
            except (ValueError, IndexError):
                return None
            return get_node_position(angle, MENU_RADIUS, center)

        def _is_cursor_over_branch(self, cursor: QPoint, branch_item: RadialMenuItem) -> bool:
            """
            Check if cursor is within hover radius of a branch or exit node.

            Applies hysteresis when ``branch_item`` is already the active
            hover target: the effective radius is expanded by
            BRANCH_HOVER_HYSTERESIS_PX so cursor jitter at the boundary cannot
            cause the dwell timer to restart / cancel repeatedly.
            """
            if not (branch_item.is_branch or branch_item.is_exit):
                return False

            # Get center of widget
            center = QPointF(self.width() / 2, self.height() / 2)

            # Exit nodes are at center, not at MENU_RADIUS
            if branch_item.is_exit:
                branch_pos = center
            else:
                # Get branch node position
                try:
                    item_index = self._items.index(branch_item)
                    angle = self._node_angles[item_index]
                    branch_pos = get_node_position(angle, MENU_RADIUS, center)
                except (ValueError, IndexError):
                    return False

            # Convert cursor to widget coords
            cursor_widget = self.mapFromGlobal(cursor)

            # Calculate distance
            dx = cursor_widget.x() - branch_pos.x()
            dy = cursor_widget.y() - branch_pos.y()
            dist_sq = dx * dx + dy * dy

            # Hysteresis: expand effective radius if this is the currently
            # hovered item, so we "stick" to it.
            effective_radius: float = float(BRANCH_HOVER_RADIUS)
            if branch_item is self._hovered_branch_item:
                effective_radius += BRANCH_HOVER_HYSTERESIS_PX

            return dist_sq <= (effective_radius * effective_radius)

        def _start_dwell_timer(self, branch_item: RadialMenuItem) -> None:
            """Start dwell timer to enter submenu after delay."""
            import time as _time
            self._hovered_branch_item = branch_item
            self._dwell_start_time = _time.monotonic()
            self._dwell_timer.start(BRANCH_DWELL_MS)
            self.update()  # Repaint to show highlight

        def _cancel_dwell_timer(self) -> None:
            """Cancel dwell timer when cursor leaves branch hover region."""
            self._dwell_timer.stop()
            self._dwell_start_time = 0.0
            # Note: Don't clear _hovered_branch_item here - let caller decide
            # This allows exit nodes to remain highlighted during activation

        def _on_dwell_timeout(self) -> None:
            """Handle dwell timer timeout - enter submenu or invoke exit action."""
            if not self._hovered_branch_item:
                return

            # Exit node - invoke its action (which calls _exit_submenu)
            if self._hovered_branch_item.is_exit:
                # Force repaint to show highlight before action
                self.update()
                QApplication.processEvents()
                self._hovered_branch_item.action()
                return

            # Branch node - enter submenu
            if self._hovered_branch_item.children:
                # Force repaint to show highlight before transition
                self.update()
                QApplication.processEvents()
                self._enter_submenu(self._hovered_branch_item)

        def _enter_submenu(self, branch_item: RadialMenuItem) -> None:
            """Push submenu onto stack and display it."""
            if not branch_item.children:
                return

            # Start branch transition animation (fade out)
            import time as _time
            self._branch_transition_start = _time.monotonic()
            self._branch_transition_active = True
            self._branch_transition_exiting = False  # Entering branch

            # Calculate branch node's screen position to use as new anchor
            center = QPointF(self.width() / 2, self.height() / 2)
            try:
                item_index = self._items.index(branch_item)
                angle = self._node_angles[item_index]
                branch_pos_widget = get_node_position(
                    angle, MENU_RADIUS, center)
                # Convert to screen coordinates
                new_anchor = self.mapToGlobal(branch_pos_widget.toPoint())
            except (ValueError, IndexError):
                # Fallback: keep current anchor if branch not found
                new_anchor = self._anchor

            # Push current menu state onto stack
            self._menu_stack.append(self._items)
            if self._anchor:
                self._anchor_stack.append(self._anchor)
            # Push current menu name for center label
            self._menu_name_stack.append(self._menu_name)

            # Update anchor to branch node's position. The widget is resized and
            # repositioned AFTER _recalculate_geometry() below so it fits the new
            # submenu's geometry rather than the parent menu's stale extents.
            self._anchor = new_anchor

            # Cursor spawned on branch node, so it will be over exit node at center
            # Don't trigger exit until cursor leaves and re-enters
            self._cursor_has_left_spawn_item = False

            # Clear just_exited tracking - we're in a new menu context now
            self._just_exited_from_label = None

            # Stop any ongoing dwell timer from parent menu
            self._cancel_dwell_timer()

            # Create exit node and add to submenu items
            exit_node = self._create_exit_node()
            # Exit node stays at center (no angle needed)

            # The newly-created exit node is the spawn item for this submenu:
            # the cursor sits on top of it the moment we open and must move
            # SPAWN_EXIT_BUFFER_PX past its outer edge before dwell is allowed.
            self._spawn_item = exit_node

            # Set new items from branch children + exit node
            self._items = [exit_node] + list(branch_item.children)
            self._highlighted_leaf_index = None
            self._hovered_branch_item = None  # Clear parent menu hover state

            # Update center label to this branch's name
            self._menu_name = branch_item.label

            # Branch transition (crossfade) handles the animation for submenu
            # navigation — no separate item stagger needed here.
            self._anim_start_time = _time.monotonic()
            self._anim_active = False

            # Reset cursor position to current global cursor in new widget coords
            # This prevents the cursor line from being offset after widget moves
            from PySide6.QtGui import QCursor
            cursor_widget = self.mapFromGlobal(QCursor.pos())
            self._last_cursor_widget_pos = QPointF(cursor_widget)

            self._recalculate_geometry()
            # Size to the new submenu geometry now that it has been recalculated.
            self._resize_and_center_on(self._anchor)
            self.update()

        def _exit_submenu(self) -> None:
            """Pop submenu from stack and restore parent menu."""
            if not self._menu_stack:
                return

            # Start branch transition animation (fade in)
            import time as _time
            self._branch_transition_start = _time.monotonic()
            self._branch_transition_active = True
            self._branch_transition_exiting = True  # Exiting branch

            # Find which branch in parent we need to debounce
            # The exit node's parent is stored when menu was entered
            exited_branch_label: str | None = None
            if len(self._menu_stack) > 0:
                parent_items = self._menu_stack[-1]
                # Find branch that has our current menu as children
                current_first_non_exit = next(
                    (item for item in self._items if not item.is_exit), None)
                if current_first_non_exit:
                    for parent_item in parent_items:
                        if parent_item.is_branch and parent_item.children:
                            first_child = next(
                                (c for c in parent_item.children), None)
                            if first_child and first_child.label == current_first_non_exit.label:
                                exited_branch_label = parent_item.label
                                break

            # Restore parent menu. The widget is resized and repositioned AFTER
            # _recalculate_geometry() below so it fits the restored parent menu's
            # geometry rather than the (typically smaller) submenu we came from.
            # Sizing here with stale extents is what clipped the parent menu.
            self._items = self._menu_stack.pop()
            if self._anchor_stack:
                self._anchor = self._anchor_stack.pop()
            # Restore parent menu name
            if self._menu_name_stack:
                self._menu_name = self._menu_name_stack.pop()

            # Track which branch to debounce in parent menu
            self._just_exited_from_label = exited_branch_label

            # Can interact with other items immediately
            self._cursor_has_left_spawn_item = True

            # The branch the cursor is sitting on (the one we exited back into)
            # is the spawn item for this restored menu — block its dwell until
            # the cursor moves clear of it. _just_exited_from_label provides
            # an additional label-based block as a belt-and-braces measure.
            self._spawn_item = None
            if exited_branch_label is not None:
                for parent_item in self._items:
                    if (
                        parent_item.is_branch
                        and parent_item.label == exited_branch_label
                    ):
                        self._spawn_item = parent_item
                        break

            # Stop any ongoing dwell timer from child menu
            self._cancel_dwell_timer()

            self._highlighted_leaf_index = None

            # Branch transition (crossfade) handles the animation for submenu
            # navigation — no separate item stagger needed here.
            self._anim_start_time = _time.monotonic()
            self._anim_active = False
            self._hovered_branch_item = None  # Clear child menu hover state

            # Reset cursor position to current global cursor in new widget coords
            # This prevents the cursor line from being offset after widget moves
            from PySide6.QtGui import QCursor
            cursor_widget = self.mapFromGlobal(QCursor.pos())
            self._last_cursor_widget_pos = QPointF(cursor_widget)

            self._recalculate_geometry()
            # Size to the restored parent menu geometry now that it has been
            # recalculated — prevents the parent menu from being clipped.
            if self._anchor:
                self._resize_and_center_on(self._anchor)
            self.update()

        def _create_exit_node(self) -> RadialMenuItem:
            """Create exit node for returning to parent menu."""
            return RadialMenuItem(
                label="Exit",
                action=self._exit_submenu,
                icon="X",
                is_exit=True,  # Requires dwell to activate
            )

        # ---------------------------------------------------------------------
        # Event Handlers (Placeholder - will implement in later phases)
        # ---------------------------------------------------------------------

        def paintEvent(self, event):
            """Paint the radial menu."""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            if not self._anchor or not self._items:
                return

            # Widget center (where anchor is in widget coords)
            center = QPointF(self.width() / 2, self.height() / 2)

            # Draw dead zone indicator (center dot)
            self._draw_dead_zone(painter, center)

            # Draw center label (multiply dark spot + text) UNDER sectors
            self._draw_center_label(painter, center)

            # Phase 2.3: Draw connection strings (cursor → anchor chain)
            self._draw_connection_strings(painter, center)

            # Draw sector slices and labels
            self._draw_sectors(painter, center)

            # Draw list panels
            self._draw_list_panels(painter, center)

            # Draw live cursor line from anchor to cursor (ON TOP of everything)
            self._draw_cursor_line(painter, center)

        def _draw_dead_zone(self, painter: QPainter, center: QPointF) -> None:
            """Draw the dead zone indicator in the center."""
            # Draw small center dot instead of large circle
            dot_radius = 4
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(COLOR_TEXT_MUTED)))
            painter.drawEllipse(center, dot_radius, dot_radius)

        def _draw_center_label(self, painter: QPainter, center: QPointF) -> None:
            """Draw the center label with a multiply-dark backdrop for readability."""
            if not self._menu_name:
                return

            text: str = self._menu_name
            font: QFont = QFont("Arial", 11, QFont.Bold)
            painter.setFont(font)
            metrics: QFontMetrics = QFontMetrics(font)
            text_width: int = metrics.horizontalAdvance(text)
            text_height: int = metrics.height()

            # Backdrop: soft radial gradient with multiply blend mode
            pad_x: int = 14
            pad_y: int = 8
            # Place below the center dot
            y_offset: float = 16.0
            bg_rect: QRectF = QRectF(
                center.x() - text_width / 2 - pad_x,
                center.y() + y_offset - pad_y,
                text_width + pad_x * 2,
                text_height + pad_y * 2,
            )

            painter.save()

            # Draw soft feathered dark spot via radial gradient
            painter.setPen(Qt.NoPen)
            gradient: QRadialGradient = QRadialGradient(bg_rect.center(), bg_rect.width() * 0.75)
            gradient.setColorAt(0.0, QColor(80, 80, 80, 200))
            gradient.setColorAt(0.5, QColor(80, 80, 80, 120))
            gradient.setColorAt(1.0, QColor(80, 80, 80, 0))
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(bg_rect, 6, 6)

            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw light-colored text
            painter.setPen(QPen(QColor(220, 220, 220)))
            painter.drawText(
                QPointF(
                    center.x() - text_width / 2,
                    center.y() + y_offset + metrics.ascent() - 1,
                ),
                text,
            )

            painter.restore()

        def _draw_cursor_line(self, painter: QPainter, center: QPointF) -> None:
            """Draw a live line from anchor to current cursor position."""
            if self._last_cursor_widget_pos is None:
                return

            # Draw line from center to cursor
            pen = QPen(QColor(COLOR_ACCENT))
            pen.setWidth(2)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(center, self._last_cursor_widget_pos)

            # Draw small circle at cursor position
            cursor_dot_radius = 6
            painter.setBrush(QBrush(QColor(COLOR_ACCENT)))
            painter.drawEllipse(self._last_cursor_widget_pos,
                                cursor_dot_radius, cursor_dot_radius)

        def _draw_connection_strings(self, painter: QPainter, center: QPointF) -> None:
            """Draw dotted lines showing anchor chain (for multi-level menus)."""
            if not self._anchor_stack:
                # No parent menus, no strings to draw
                return

            # Get cursor position in widget coords (we'll draw from cursor to anchors)
            # For now, just draw from current anchor to parent anchors
            # Multi-segment: current anchor ╌╌ parent1 ╌╌ parent2 ╌╌ root

            pen = QPen(QColor(COLOR_TEXT_MUTED))
            pen.setWidth(1)
            pen.setStyle(Qt.DotLine)  # Dotted line
            painter.setPen(pen)

            # Draw lines from current anchor back through the stack
            prev_anchor = center  # Current menu anchor (widget center)
            for parent_anchor in reversed(self._anchor_stack):
                # Convert parent anchor (screen coords) to widget coords
                parent_widget = self.mapFromGlobal(parent_anchor)
                painter.drawLine(prev_anchor, QPointF(parent_widget))
                prev_anchor = QPointF(parent_widget)

        def _draw_sectors(self, painter: QPainter, center: QPointF) -> None:
            """Draw sector slices with highlighting."""
            if not self._node_angles:
                return

            # Calculate branch transition opacity (global fade)
            branch_opacity = self._get_branch_transition_opacity()

            # Get leaf nodes
            leaf_nodes = [item for item in self._items if item.is_leaf]

            for i, item in enumerate(self._items):
                # Skip list nodes (handled by _draw_list_panels)
                if item.is_list:
                    continue

                angle = self._node_angles[i] if i < len(
                    self._node_angles) else 0

                # Fade-only animation (scale removed)
                opacity = 1.0

                # Apply branch transition opacity (global fade)
                opacity *= branch_opacity

                # Skip drawing if not yet visible
                if opacity <= 0.0:
                    continue

                # Save painter state for opacity
                painter.save()
                painter.setOpacity(opacity)

                # Exit nodes are drawn at center (anchor), not at ring radius
                if item.is_exit:
                    pos = center  # Exit node at center
                else:
                    # Leaf nodes use their assigned ring radius; branch nodes stay at MENU_RADIUS
                    node_radius: float = self._node_radii[i] if i < len(self._node_radii) else float(MENU_RADIUS)
                    pos = get_node_position(angle, node_radius, center)

                # Determine if this node is highlighted
                is_highlighted = False
                leaf_index_for_anim = None  # Track leaf index for animation
                # Leaf nodes: highlight via pizza slice selection
                if item.is_leaf:
                    leaf_index = leaf_nodes.index(item)
                    leaf_index_for_anim = leaf_index
                    is_highlighted = (
                        leaf_index == self._highlighted_leaf_index)
                # Branch/exit nodes: highlight if being hovered (dwell in progress)
                elif (item.is_branch or item.is_exit) and item == self._hovered_branch_item:
                    is_highlighted = True

                # Apply highlight animation scale (only for leaf nodes)
                highlight_scale = 1.0
                if item.is_leaf:
                    highlight_scale = self._get_highlight_scale(
                        leaf_index_for_anim, is_highlighted)

                # Draw pizza slice background for highlighted leaf (DEBUG only)
                if DEBUG_PIZZA_SLICE and is_highlighted and item.is_leaf and self._slice_boundaries:
                    leaf_index = leaf_nodes.index(item)
                    lower, upper = self._slice_boundaries[leaf_index]
                    self._draw_pizza_slice(painter, center, lower, upper)

                # Branch nodes get special rendering as circles (matching exit nodes)
                if item.is_branch:
                    # Unified circle render via DwellProgressNode so visual
                    # geometry matches hover detection geometry exactly.
                    # SVG icons are too large for branch circles — use center dot.
                    branch_icon: str | None = item.icon if item.icon and not item.icon.endswith(".svg") else None
                    icon_font = QFont(
                        "Arial", EXIT_ICON_FONT_SIZE,
                        QFont.Bold if is_highlighted else QFont.Normal,
                    ) if branch_icon else None
                    self._dwell_node_renderer.paint(
                        painter,
                        pos,
                        progress=self._get_dwell_progress(item),
                        highlighted=is_highlighted,
                        scale=1.0,
                        icon=branch_icon,
                        icon_font=icon_font,
                        center_dot_radius=(
                            0.0 if branch_icon else float(BRANCH_DOT_RADIUS)),
                    )

                    # Draw label above circle (always bold + outlined)
                    label_font = QFont(
                        "Arial", BRANCH_LABEL_FONT_SIZE, QFont.Bold)
                    painter.setFont(label_font)
                    label_y = pos.y() - BRANCH_LABEL_OFFSET
                    label_rect = QRectF(pos.x() - 50, label_y - 10, 100, 20)
                    _draw_label_pill_gradient(painter, label_rect)
                    draw_text_with_outline(
                        painter, label_rect, Qt.AlignCenter, item.label,
                        COLOR_ACCENT if is_highlighted else COLOR_TEXT_PRIMARY
                    )
                    painter.restore()  # Restore opacity
                    continue  # Skip normal squircle rendering

                # Exit nodes get special rendering as a circle at center
                if item.is_exit:
                    icon_glyph = item.icon if item.icon and not item.icon.endswith(".svg") else "✕"
                    icon_font = QFont(
                        "Arial", EXIT_ICON_FONT_SIZE,
                        QFont.Bold if is_highlighted else QFont.Normal,
                    )
                    self._dwell_node_renderer.paint(
                        painter,
                        pos,
                        progress=self._get_dwell_progress(item),
                        highlighted=is_highlighted,
                        scale=1.0,
                        icon=icon_glyph,
                        icon_font=icon_font,
                    )
                    painter.restore()  # Restore opacity
                    continue  # Skip normal squircle rendering

                # Prepare text and font
                if is_highlighted:
                    font = QFont("Arial", NODE_FONT_SIZE_HIGHLIGHT, QFont.Bold)
                else:
                    font = QFont("Arial", NODE_FONT_SIZE)
                painter.setFont(font)

                # Icon if present — separate from label for SVG/emoji rendering
                text = item.label

                # Measure text to size squircle (label + optional icon area)
                metrics = painter.fontMetrics()
                text_width = metrics.horizontalAdvance(text) + _icon_width_contribution(item.icon)
                text_height = metrics.height()

                # Squircle dimensions with padding
                squircle_width = text_width + NODE_PADDING_X * 2
                squircle_height = text_height + NODE_PADDING_Y * 2
                corner_radius = NODE_CORNER_RADIUS

                # Apply highlight scale only
                final_scale = highlight_scale
                if is_highlighted:
                    final_scale *= HIGHLIGHT_SCALE

                squircle_width *= final_scale
                squircle_height *= final_scale

                # Draw squircle (rounded rectangle) with soft multiply gradient
                squircle_rect = QRectF(
                    pos.x() - squircle_width / 2,
                    pos.y() - squircle_height / 2,
                    squircle_width,
                    squircle_height
                )

                # Flat 50% black fill, multiplicative blend
                painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 127)))
                painter.drawRoundedRect(
                    squircle_rect, corner_radius, corner_radius)

                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                # Draw border
                if is_highlighted:
                    painter.setPen(QPen(QColor(COLOR_ACCENT), 2))
                    painter.setBrush(Qt.NoBrush)
                else:
                    painter.setPen(QPen(QColor(COLOR_BORDER), 1))
                    painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(
                    squircle_rect, corner_radius, corner_radius)

                # Draw icon left-aligned if present
                text_color = COLOR_ACCENT if is_highlighted else COLOR_TEXT_PRIMARY
                icon_shift: float = 0.0
                if item.icon:
                    icon_rect = QRectF(
                        squircle_rect.x() + NODE_PADDING_X / 2.0,
                        squircle_rect.y(),
                        ICON_AREA_SIZE + ICON_TEXT_GAP,
                        squircle_rect.height(),
                    )
                    _draw_icon(painter, item.icon, icon_rect, COLOR_ACCENT)
                    icon_shift = ICON_AREA_SIZE + ICON_TEXT_GAP + NODE_PADDING_X / 2.0

                # Draw label text left-aligned after icon area
                label_x: float = squircle_rect.x() + icon_shift
                label_rect: QRectF = QRectF(
                    label_x, squircle_rect.y(),
                    squircle_rect.width() - icon_shift - NODE_PADDING_X / 2.0,
                    squircle_rect.height(),
                )
                painter.setFont(font)
                painter.setPen(QColor(text_color))
                painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

                # Restore opacity
                painter.restore()

        def _draw_list_panels(self, painter: QPainter, center: QPointF) -> None:
            """Draw all list panel containers and their buttons."""
            branch_opacity: float = self._get_branch_transition_opacity()

            # Collect list nodes and their item indices
            list_nodes: list[tuple[int, RadialMenuItem]] = [
                (i, item) for i, item in enumerate(self._items) if item.is_list
            ]

            for panel_idx, (container_idx, container) in enumerate(list_nodes):
                if panel_idx >= len(self._list_panel_rects):
                    continue
                panel_rect: QRectF = self._list_panel_rects[panel_idx]
                button_rects: list[QRectF] = self._list_button_rects[panel_idx]

                # Offset to widget coordinates
                widget_panel: QRectF = QRectF(
                    center.x() + panel_rect.x(),
                    center.y() + panel_rect.y(),
                    panel_rect.width(),
                    panel_rect.height())

                # Fade with branch transition
                painter.save()
                painter.setOpacity(branch_opacity)

                # Draw panel background — 50% black multiplicative
                painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 127)))
                bg_rect: QRectF = QRectF(widget_panel)
                painter.drawRoundedRect(bg_rect, 6, 6)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                # Draw panel border
                painter.setPen(QPen(QColor(COLOR_BORDER), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(bg_rect, 6, 6)

                # Draw header label
                header_font: QFont = QFont("Arial", BRANCH_LABEL_FONT_SIZE, QFont.Bold)
                painter.setFont(header_font)
                header_rect: QRectF = QRectF(
                    widget_panel.x(), widget_panel.y(),
                    widget_panel.width(), float(LIST_HEADER_HEIGHT))
                _draw_label_pill_gradient(painter, header_rect)
                draw_text_with_outline(
                    painter, header_rect, Qt.AlignCenter,
                    container.label, COLOR_ACCENT)

                # Draw separator line under header
                sep_y: float = widget_panel.y() + LIST_HEADER_HEIGHT
                painter.setPen(QPen(QColor(COLOR_BORDER), 1))
                painter.drawLine(
                    QPointF(widget_panel.x() + 4, sep_y),
                    QPointF(widget_panel.right() - 4, sep_y))

                # Draw each button
                for btn_idx, child in enumerate(container.children):
                    btn_rect: QRectF = QRectF(
                        widget_panel.x() + button_rects[btn_idx].x(),
                        widget_panel.y() + button_rects[btn_idx].y(),
                        button_rects[btn_idx].width(),
                        button_rects[btn_idx].height())

                    # All buttons fade together (no scale stagger)
                    btn_opacity: float = 1.0 * branch_opacity

                    if btn_opacity <= 0.0:
                        continue

                    painter.save()
                    painter.setOpacity(btn_opacity)

                    # Check if this specific button is highlighted
                    is_hl: bool = (
                        container_idx == self._highlighted_list_container
                        and btn_idx == self._highlighted_list_button
                    )

                    # Scale rect from center for highlight only
                    effective_scale: float = HIGHLIGHT_SCALE if is_hl else 1.0
                    sw: float = btn_rect.width() * effective_scale
                    sh: float = btn_rect.height() * effective_scale
                    dx: float = (sw - btn_rect.width()) / 2.0
                    dy: float = (sh - btn_rect.height()) / 2.0
                    scaled_rect: QRectF = QRectF(
                        btn_rect.x() - dx, btn_rect.y() - dy, sw, sh)

                    # Draw squircle button with 50% black multiplicative fill
                    painter.setCompositionMode(QPainter.CompositionMode_Multiply)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(QColor(0, 0, 0, 127)))
                    painter.drawRoundedRect(scaled_rect, NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                    # Draw border
                    if is_hl:
                        painter.setPen(QPen(QColor(COLOR_ACCENT), 2))
                        painter.setBrush(Qt.NoBrush)
                    else:
                        painter.setPen(QPen(QColor(COLOR_BORDER), 1))
                        painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(scaled_rect, NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)

                    # Button text with icon
                    btn_font: QFont = QFont(
                        "Arial",
                        NODE_FONT_SIZE_HIGHLIGHT if is_hl else NODE_FONT_SIZE,
                        QFont.Bold if is_hl else QFont.Normal)
                    painter.setFont(btn_font)
                    btn_text_color = COLOR_ACCENT if is_hl else COLOR_TEXT_PRIMARY
                    icon_shift: float = 0.0
                    if child.icon:
                        icon_rect = QRectF(
                            scaled_rect.x() + NODE_PADDING_X / 2.0,
                            scaled_rect.y(),
                            ICON_AREA_SIZE + ICON_TEXT_GAP,
                            scaled_rect.height(),
                        )
                        _draw_icon(painter, child.icon, icon_rect, COLOR_ACCENT)
                        icon_shift = ICON_AREA_SIZE + ICON_TEXT_GAP + NODE_PADDING_X / 2.0

                    label_x: float = scaled_rect.x() + icon_shift
                    label_rect: QRectF = QRectF(
                        label_x, scaled_rect.y(),
                        scaled_rect.width() - icon_shift - NODE_PADDING_X / 2.0,
                        scaled_rect.height(),
                    )
                    painter.setFont(btn_font)
                    painter.setPen(QColor(btn_text_color))
                    painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, child.label)

                    painter.restore()

                painter.restore()

        def _draw_pizza_slice(
            self,
            painter: QPainter,
            center: QPointF,
            lower_angle: float,
            upper_angle: float,
        ) -> None:
            """Draw a highlighted pizza slice background."""
            painter.setPen(Qt.NoPen)
            painter.setBrush(
                QBrush(QColor(COLOR_ACCENT + "20")))  # 12.5% alpha

            # Create path for pizza slice using our coordinate system throughout
            # Our system: 0° = up, clockwise
            path = QPainterPath()

            # Handle wrap-around for angle calculation
            angle_span = upper_angle - lower_angle
            if angle_span < 0:
                angle_span += 360

            # Draw slice as a series of line segments
            # Start at inner radius (dead zone edge)
            start_inner = get_node_position(
                lower_angle, DEAD_ZONE_RADIUS, center)
            path.moveTo(start_inner)

            # Line to outer radius
            start_outer = get_node_position(
                lower_angle, MENU_RADIUS + 30, center)
            path.lineTo(start_outer)

            # Arc along outer edge (draw as many line segments)
            # One segment per 5 degrees, min 8
            segments = max(int(angle_span / 5), 8)
            for i in range(1, segments + 1):
                angle = lower_angle + (angle_span * i / segments)
                if angle >= 360:
                    angle -= 360
                point = get_node_position(angle, MENU_RADIUS + 30, center)
                path.lineTo(point)

            # Line back to inner radius
            end_inner = get_node_position(
                upper_angle, DEAD_ZONE_RADIUS, center)
            path.lineTo(end_inner)

            # Arc back along inner edge
            for i in range(segments, -1, -1):
                angle = lower_angle + (angle_span * i / segments)
                if angle >= 360:
                    angle -= 360
                point = get_node_position(angle, DEAD_ZONE_RADIUS, center)
                path.lineTo(point)

            path.closeSubpath()
            painter.drawPath(path)

        def _get_animation_progress(self) -> float:
            """Get current animation progress (0.0 to 1.0)."""
            if not self._anim_active:
                return 1.0

            import time as _time
            elapsed_ms = (_time.monotonic() - self._anim_start_time) * 1000.0
            progress = elapsed_ms / ANIM_DURATION_MS
            return min(1.0, progress)

        def _get_dwell_progress(self, item: RadialMenuItem) -> float:
            """
            Return dwell progress 0.0 → 1.0 for ``item``.

            Mirrors the underlying QTimer 1:1 — when this returns 1.0 the
            timeout has fired (or is firing this same frame). Returns 0.0 for
            any item that is not the current dwell target.
            """
            if (
                self._hovered_branch_item is not item
                or self._dwell_start_time <= 0.0
                or BRANCH_DWELL_MS <= 0
            ):
                return 0.0
            import time as _time
            elapsed_ms = (_time.monotonic() - self._dwell_start_time) * 1000.0
            return max(0.0, min(1.0, elapsed_ms / BRANCH_DWELL_MS))

        def _get_highlight_anim_progress(self) -> float:
            """Get current highlight animation progress (0.0 to 1.0)."""
            if not self._highlight_anim_active:
                return 1.0

            import time as _time
            elapsed_ms = (_time.monotonic() -
                          self._highlight_anim_start) * 1000.0
            progress = elapsed_ms / HIGHLIGHT_ANIM_MS
            return min(1.0, progress)

        def _get_highlight_scale(self, item_index: int, is_highlighted: bool) -> float:
            """Calculate animated scale for highlight transitions."""
            # No animation needed if no transition
            if not self._highlight_anim_active:
                return 1.0

            progress = self._get_highlight_anim_progress()
            eased = self._ease_out_cubic(progress)

            # Check if this item is transitioning
            was_highlighted = (self._prev_highlighted_index == item_index)

            if was_highlighted and not is_highlighted:
                # Fading out highlight: 1.0 + bonus → 1.0
                return 1.0 + HIGHLIGHT_SCALE_BONUS * (1.0 - eased)
            elif not was_highlighted and is_highlighted:
                # Fading in highlight: 1.0 → 1.0 + bonus
                return 1.0 + HIGHLIGHT_SCALE_BONUS * eased

            return 1.0  # No transition for this item

        def _get_branch_transition_progress(self) -> float:
            """Get current branch transition animation progress (0.0 to 1.0)."""
            if not self._branch_transition_active:
                return 1.0

            import time as _time
            elapsed_ms = (_time.monotonic() -
                          self._branch_transition_start) * 1000.0
            duration = BRANCH_FADE_OUT_MS if not self._branch_transition_exiting else BRANCH_FADE_IN_MS
            progress = elapsed_ms / duration
            return min(1.0, progress)

        def _get_branch_transition_opacity(self) -> float:
            """Calculate opacity for branch transition (fade out then fade in)."""
            if not self._branch_transition_active:
                return 1.0

            progress = self._get_branch_transition_progress()
            eased = self._ease_out_cubic(progress)

            # Always fade in (items appear from 0 to 1)
            return eased

        @staticmethod
        def _ease_out_cubic(t: float) -> float:
            """Cubic ease-out function for smooth animation."""
            return 1.0 - pow(1.0 - t, 3)

        def _poll_cursor(self) -> None:
            """Poll cursor position every frame for smooth cursor line updates."""
            if not self.isVisible() or not self._anchor:
                return

            import time as _time
            from PySide6.QtGui import QCursor
            from ported.utils.win32_key_state import is_vk_down

            # Get global cursor position
            cursor_screen = QCursor.pos()

            # Convert to widget coordinates
            cursor_widget = self.mapFromGlobal(cursor_screen)
            self._update_cursor_state(cursor_screen, QPointF(cursor_widget))

            # Update animations and request repaint if any are active
            any_anim_active = False

            if self._anim_active:
                progress = self._get_animation_progress()
                if progress >= 1.0:
                    self._anim_active = False
                else:
                    any_anim_active = True

            if self._highlight_anim_active:
                progress = self._get_highlight_anim_progress()
                if progress >= 1.0:
                    self._highlight_anim_active = False
                else:
                    any_anim_active = True

            if self._branch_transition_active:
                progress = self._get_branch_transition_progress()
                if progress >= 1.0:
                    self._branch_transition_active = False
                else:
                    any_anim_active = True

            if self._flick_mode:
                if self._highlighted_leaf_index is not None:
                    self.hide_and_invoke()
                    return
                if _time.monotonic() >= self._flick_deadline:
                    self.hide_and_invoke()
                    return
            elif self._trigger_vk is not None and not is_vk_down(self._trigger_vk):
                self.hide_and_invoke()
                return

            # ---- Escape key (VK 0x1B) via Win32 poll (no grabKeyboard) ----
            if is_vk_down(0x1B):
                self._cursor_poll_timer.stop()
                self.hide()
                return

            if any_anim_active:
                self.update()

            # Trigger repaint to update cursor line
            self.update()

        def _update_cursor_state(self, cursor_screen: QPoint, cursor_widget: QPointF) -> None:
            """Update branch hover and highlighted leaf from the current cursor."""
            self._last_cursor_widget_pos = QPointF(cursor_widget)

            # --- LIST BUTTON HOVER DETECTION ---
            self._highlighted_list_container = None
            self._highlighted_list_button = None

            if self._list_panel_rects:
                center: QPointF = QPointF(self.width() / 2, self.height() / 2)
                # Build list nodes in the same order as _draw_list_panels so
                # panel_idx and container_idx are consistent.
                list_nodes: list[tuple[int, RadialMenuItem]] = [
                    (i, item) for i, item in enumerate(self._items) if item.is_list
                ]
                for panel_idx, (container_idx, _container) in enumerate(list_nodes):
                    if panel_idx >= len(self._list_panel_rects):
                        continue
                    panel_rect: QRectF = self._list_panel_rects[panel_idx]

                    # Offset panel rect to widget coordinates (ring-relative → widget)
                    widget_panel: QRectF = QRectF(
                        center.x() + panel_rect.x(),
                        center.y() + panel_rect.y(),
                        panel_rect.width(),
                        panel_rect.height())

                    if widget_panel.contains(QPointF(cursor_widget)):
                        # Button rects are stored as offsets from panel origin,
                        # so add widget_panel position to convert to widget coords.
                        button_rects: list[QRectF] = self._list_button_rects[panel_idx]
                        for btn_idx, btn_rect in enumerate(button_rects):
                            widget_btn: QRectF = QRectF(
                                widget_panel.x() + btn_rect.x(),
                                widget_panel.y() + btn_rect.y(),
                                btn_rect.width(),
                                btn_rect.height())
                            if widget_btn.contains(QPointF(cursor_widget)):
                                # Store the actual item index so _draw_list_panels
                                # and hide_and_invoke can compare/use it directly.
                                self._highlighted_list_container = container_idx
                                self._highlighted_list_button = btn_idx
                                self._highlighted_leaf_index = None
                                self._hovered_branch_item = None
                                self.update()
                                return

            hovered_branch: RadialMenuItem | None = None
            # Check the currently-hovered item FIRST so hysteresis can keep
            # us locked to it through tiny boundary jitter. Only if it has
            # truly left (incl. hysteresis margin) do we look elsewhere.
            if self._hovered_branch_item is not None:
                if self._is_cursor_over_branch(cursor_screen, self._hovered_branch_item):
                    hovered_branch = self._hovered_branch_item
            if hovered_branch is None:
                for item in self._items:
                    if item is self._hovered_branch_item:
                        continue  # already tested above
                    if (item.is_branch or item.is_exit) and self._is_cursor_over_branch(cursor_screen, item):
                        hovered_branch = item
                        break

            if not hovered_branch and not self._cursor_has_left_spawn_item:
                self._cursor_has_left_spawn_item = True

            # Distance-based spawn-item release: once the cursor has moved
            # clear of the spawn item's outer edge by SPAWN_EXIT_BUFFER_PX,
            # we consider it "left" and dwell on that item is unblocked.
            # This is robust against per-frame jitter at the boundary, which
            # the simple "is cursor over branch?" check is not.
            if self._spawn_item is not None:
                spawn_pos = self._get_item_widget_pos(self._spawn_item)
                if spawn_pos is not None:
                    dx = cursor_widget.x() - spawn_pos.x()
                    dy = cursor_widget.y() - spawn_pos.y()
                    release_radius = BRANCH_NODE_RADIUS + SPAWN_EXIT_BUFFER_PX
                    if (dx * dx + dy * dy) > (release_radius * release_radius):
                        self._spawn_item = None

            if self._just_exited_from_label and (not hovered_branch or hovered_branch.label != self._just_exited_from_label):
                self._just_exited_from_label = None

            if hovered_branch:
                # Block dwell while cursor still sits on the spawn item
                # (e.g. the new exit node right after entering a submenu, or
                # the parent branch right after exiting back to it).
                if hovered_branch is self._spawn_item:
                    pass
                elif self._just_exited_from_label and hovered_branch.label == self._just_exited_from_label:
                    pass
                elif self._cursor_has_left_spawn_item and self._hovered_branch_item != hovered_branch:
                    self._start_dwell_timer(hovered_branch)
            elif self._hovered_branch_item is not None:
                self._cancel_dwell_timer()
                self._hovered_branch_item = None
                self.update()

            old_highlight = self._highlighted_leaf_index
            if not hovered_branch and self._leaf_angles:
                # Ring-aware highlight detection:
                # 1. Compute cursor distance from anchor
                # 2. Check dead zone
                # 3. Find closest ring by distance
                # 4. Match angle within that ring's per-ring slice boundaries
                # 5. Map ring-local leaf index → global flat leaf index
                dx: float = cursor_screen.x() - self._anchor.x()
                dy: float = cursor_screen.y() - self._anchor.y()
                distance: float = math.sqrt(dx * dx + dy * dy)

                if distance < DEAD_ZONE_RADIUS:
                    self._highlighted_leaf_index = None
                elif self._ring_radii and len(self._ring_slice_boundaries) > 0:
                    # Multi-ring: find closest ring by distance
                    best_ring: int = 0
                    best_diff: float = abs(distance - self._ring_radii[0])
                    for ri in range(1, len(self._ring_radii)):
                        diff: float = abs(distance - self._ring_radii[ri])
                        if diff < best_diff:
                            best_diff = diff
                            best_ring = ri

                    # Compute flat leaf index offset for this ring
                    leaf_offset: int = 0
                    for ri in range(best_ring):
                        leaf_offset += len(self._ring_item_indices[ri])

                    # Match angle within this ring's slice boundaries
                    cursor_angle: float = cursor_to_angle(
                        cursor_screen, self._anchor)
                    ring_boundaries = self._ring_slice_boundaries[best_ring]
                    ring_angles: list[float] = [
                        self._node_angles[i] for i in self._ring_item_indices[best_ring]
                    ]

                    # Cursor direction vector (normalized)
                    cursor_dx: float = dx / distance
                    cursor_dy: float = dy / distance

                    ring_highlight: int | None = None
                    for li, (lower, upper) in enumerate(ring_boundaries):
                        if angle_in_slice(cursor_angle, lower, upper):
                            item_angle: float = ring_angles[li]
                            item_angle_rad: float = math.radians(item_angle)
                            item_dx: float = math.sin(item_angle_rad)
                            item_dy: float = -math.cos(item_angle_rad)
                            dot: float = cursor_dx * item_dx + cursor_dy * item_dy
                            if dot >= 0:
                                ring_highlight = leaf_offset + li
                                break

                    self._highlighted_leaf_index = ring_highlight
                else:
                    # Single ring or fallback: use original flat detection
                    self._highlighted_leaf_index = get_highlighted_leaf(
                        cursor_screen,
                        self._anchor,
                        self._leaf_angles,
                        self._slice_boundaries,
                    )
            else:
                self._highlighted_leaf_index = None

            if old_highlight != self._highlighted_leaf_index:
                if self._highlighted_leaf_index is not None:
                    self.highlightChanged.emit(self._highlighted_leaf_index)

                import time as _time
                self._highlight_anim_start = _time.monotonic()
                self._highlight_anim_active = True
                self._prev_highlighted_index = old_highlight
                self.update()

        def mouseMoveEvent(self, event):
            """Track cursor position and update highlighting."""
            if not self._anchor:
                super().mouseMoveEvent(event)
                return

            cursor_screen = self.mapToGlobal(event.position().toPoint())
            self._update_cursor_state(cursor_screen, QPointF(event.position()))
            super().mouseMoveEvent(event)

        def keyReleaseEvent(self, event):
            """Key release — dead code without grabKeyboard() (Win32 poll instead)."""
            super().keyReleaseEvent(event)

        def keyPressEvent(self, event):
            """Key press — dead code without grabKeyboard() (Win32 poll instead)."""
            super().keyPressEvent(event)


# =============================================================================
# STANDALONE TEST
# =============================================================================

def test_geometry():
    """Test geometry calculations."""
    print("\n" + "="*60)
    print("GEOMETRY TEST - Phase 1.2")
    print("="*60)

    # Test cursor_to_angle
    if HAS_QT:
        anchor = QPoint(100, 100)

        test_cases = [
            (QPoint(100, 50), "Up", 0.0),
            (QPoint(150, 100), "Right", 90.0),
            (QPoint(100, 150), "Down", 180.0),
            (QPoint(50, 100), "Left", 270.0),
        ]

        print("\ncursor_to_angle tests:")
        for cursor, label, expected in test_cases:
            angle = cursor_to_angle(cursor, anchor)
            status = "OK" if abs(angle - expected) < 1.0 else "FAIL"
            print(
                f"  {status} {label:6s}: {angle:6.1f} deg (expected {expected:6.1f} deg)")

    # Test distribute_node_angles
    items = [
        RadialMenuItem(label=f"Item {i}", action=lambda: None)
        for i in range(4)
    ]
    angles = distribute_node_angles(items)
    print(f"\nDistribute 4 nodes evenly:")
    for i, angle in enumerate(angles):
        print(f"  Node {i}: {angle:6.1f} deg")

    # Test slice boundaries
    leaf_angles = [0.0, 90.0, 180.0, 270.0]
    boundaries = calculate_slice_boundaries(leaf_angles)
    print(f"\nSlice boundaries for {leaf_angles}:")
    for i, (lower, upper) in enumerate(boundaries):
        print(f"  Slice {i}: {lower:6.1f} to {upper:6.1f} deg")

    # Test angle_in_slice
    print(f"\nangle_in_slice tests:")
    test_angles = [45.0, 135.0, 315.0]
    for test_angle in test_angles:
        for i, (lower, upper) in enumerate(boundaries):
            if angle_in_slice(test_angle, lower, upper):
                print(f"  {test_angle} deg is in slice {i}")
                break

    print("="*60 + "\n")


def test_standalone():
    """
    Test the radial menu in standalone mode.

    Run with: python radial_menu.py
    Or from 3DCoat's Python: python.exe radial_menu.py
    """
    if not HAS_QT:
        print("ERROR: PySide6 not available")
        return

    import sys

    # First test geometry
    test_geometry()

    # Create application
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Create test menu items
    def action_1():
        print(">>> Decimate 50% invoked")
        app.quit()

    def action_2():
        print(">>> Resample Half invoked")
        app.quit()

    def action_3():
        print(">>> Ghost Toggle invoked")
        app.quit()

    def action_4():
        print(">>> To Surface invoked")
        app.quit()

    items = [
        RadialMenuItem(label="Decimate 50%", action=action_1, icon="🔻"),
        RadialMenuItem(label="Resample Half", action=action_2, icon="🔄"),
        RadialMenuItem(label="Ghost Toggle", action=action_3, icon="👻"),
        RadialMenuItem(label="To Surface", action=action_4, icon="⚙️"),
    ]

    # Create and show widget
    menu = RadialMenuWidget()
    menu.set_items(items)

    # Show at screen center
    screen = app.primaryScreen().geometry()
    center = QPoint(screen.width() // 2, screen.height() // 2)
    menu.show_at(center)

    print("\n" + "="*60)
    print("RADIAL MENU TEST - Phase 1.3 (Painting)")
    print("="*60)
    print("The menu should appear at screen center with:")
    print("  • Dead zone circle in center")
    print("  • Four sectors with icons and labels")
    print("  • Dotted separator lines")
    print("\nMove mouse to highlight sectors.")
    print("Press any key while highlighting to invoke action.")
    print("Press Escape to close without invoking.")
    print("="*60 + "\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    test_standalone()
