"""
Radial menu geometry and angle calculations.

Handles all mathematical operations for radial menu positioning and selection.
"""

from __future__ import annotations
import math

try:
    from PySide6.QtCore import QPoint, QPointF
    HAS_QT = True
except ImportError:
    HAS_QT = False
    QPoint = None
    QPointF = None

# =============================================================================
# CONSTANTS
# =============================================================================

DEAD_ZONE_RADIUS: int = 50          # Pixels - no selection within this radius
MENU_RADIUS: int = 150              # Pixels - distance from anchor to item centers
BRANCH_HOVER_RADIUS: int = 40       # Pixels - hover detection radius for branches
# Milliseconds - dwell time to enter/exit submenu
BRANCH_DWELL_MS: int = 250

# =============================================================================
# ANGLE CALCULATIONS
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
        leaf_angles: Sorted list of leaf node angles

    Returns:
        List of (lower_bound, upper_bound) tuples for each leaf
    """
    if not leaf_angles:
        return []

    n = len(leaf_angles)
    boundaries: list[tuple[float, float]] = []

    for i in range(n):
        prev_angle = leaf_angles[i - 1] if i > 0 else leaf_angles[-1]
        curr_angle = leaf_angles[i]
        next_angle = leaf_angles[(i + 1) % n]

        # Calculate bisecting angles
        # Lower bound: midpoint between previous and current
        if prev_angle > curr_angle:
            # Wrap around 360°
            lower = (prev_angle + curr_angle + 360) / 2
            if lower >= 360:
                lower -= 360
        else:
            lower = (prev_angle + curr_angle) / 2

        # Upper bound: midpoint between current and next
        if curr_angle > next_angle:
            # Wrap around 360°
            upper = (curr_angle + next_angle + 360) / 2
            if upper >= 360:
                upper -= 360
        else:
            upper = (curr_angle + next_angle) / 2

        boundaries.append((lower, upper))

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
    if lower <= upper:
        # Normal case: no wrap-around
        return lower <= angle < upper
    else:
        # Wrap-around case: slice crosses 0°
        return angle >= lower or angle < upper


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

    # Find which slice contains cursor
    for i, (lower, upper) in enumerate(slice_boundaries):
        if angle_in_slice(cursor_angle, lower, upper):
            return i

    return None


def distribute_node_angles(nodes: list) -> list[float]:
    """
    Assign angles to nodes: use explicit if specified, else distribute evenly.

    First node at 0° (up), subsequent nodes proceed clockwise.

    Args:
        nodes: List of menu items (must have .angle attribute)

    Returns:
        List of angles (one per node)
    """
    angles: list[float] = []
    explicit_count = sum(1 for node in nodes if node.angle is not None)
    auto_count = len(nodes) - explicit_count

    if auto_count > 0:
        # Calculate even distribution for auto nodes
        angle_step = 360.0 / len(nodes)

    auto_index = 0
    for i, node in enumerate(nodes):
        if node.angle is not None:
            # Use explicit angle
            angles.append(node.angle)
        else:
            # Auto-distribute
            angles.append(auto_index * angle_step)
            auto_index += 1

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
