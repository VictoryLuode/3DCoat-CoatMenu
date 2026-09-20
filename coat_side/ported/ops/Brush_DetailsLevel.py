"""
Brush_DetailsLevel Operator

Manage dynamic subdivision details level for sculpt brushes.

Supports:
- Increment/decrement detail level
- Apply settings to current brush or all brushes
- Sync with persistent settings cache

Uses brush settings cache for persistent state across sessions.
"""
from __future__ import annotations

from enum import Enum
from ported.utils.brush_settings_utils import (
    apply_details_level_current,
    BrushSettingsUtils,
)
from ported.utils.lks_settings import (
    get_brush_settings,
    save_brush_settings,
    reload_brush_settings,
)
from ported.utils.object_utils import validate_and_ensure_surface_mode
from ported.utils.coat_ui_utils import show_message, show_error


# =============================================================================
# CONSTANTS
# =============================================================================

MIN_DETAILS_LEVEL: float = -1.0


# =============================================================================
# OPERATION MODES
# =============================================================================

class DetailsLevelMode(Enum):
    """Modes for details level adjustment."""
    INCREMENT = "increment"
    DECREMENT = "decrement"
    SET = "set"


class ApplyScope(Enum):
    """Scope for applying brush settings."""
    CURRENT = "current"
    ALL = "all"


# =============================================================================
# MAIN OPERATORS
# =============================================================================

def adjust_details_level(
    mode: DetailsLevelMode = DetailsLevelMode.INCREMENT,
    value: float | None = None,
    apply_scope: ApplyScope = ApplyScope.CURRENT,
) -> float | None:
    """
    Adjust the brush details level.

    Args:
        mode: INCREMENT, DECREMENT, or SET
        value: Target value for SET mode (ignored for inc/dec)
        apply_scope: CURRENT brush only or ALL brushes

    Returns:
        New details level value, or None if failed
    """
    # Ensure surface mode for dynamic subdiv
    if not validate_and_ensure_surface_mode():
        show_error("Select a sculpt object in surface mode", 2000)
        return None

    # Force reload from disk to get latest value
    reload_brush_settings()
    settings = get_brush_settings()
    current: float = float(settings.details_level)

    # Calculate new value (no upper max — only floor at MIN_DETAILS_LEVEL)
    if mode == DetailsLevelMode.INCREMENT:
        new_value: float = current + 0.5
    elif mode == DetailsLevelMode.DECREMENT:
        new_value = max(MIN_DETAILS_LEVEL, current - 0.5)
    else:  # SET
        if value is None:
            show_error("Value required for SET mode", 2000)
            return None
        new_value = max(MIN_DETAILS_LEVEL, float(value))

    # Update and save settings
    settings.details_level = new_value
    settings.auto_subdivide = True
    save_brush_settings()

    # Always update the live current-brush UI first (hardened for conditional
    # AutoSubdivide → DetailsLevel). Then optionally sync all brush types.
    apply_details_level_current(float(new_value))

    if apply_scope == ApplyScope.ALL:
        BrushSettingsUtils.apply_global_brush_settings(
            True,  # auto_subdivide
            new_value,
            settings.remove_stretching,
        )

    show_message(f"Details Level: {new_value}", 1000)
    return new_value


def apply_all_brush_settings() -> None:
    """
    Apply cached dynamic subdiv settings to all brush types.

    Reads auto_subdivide, details_level, and remove_stretching from cache.
    Also refreshes the live current-brush UI so the visible number updates.
    """
    settings = get_brush_settings()

    if settings.auto_subdivide:
        apply_details_level_current(float(settings.details_level))

    BrushSettingsUtils.apply_global_brush_settings(
        settings.auto_subdivide,
        settings.details_level,
        settings.remove_stretching,
    )

    sub_status: str = "ON" if settings.auto_subdivide else "OFF"
    stretch_status: str = "ON" if settings.remove_stretching else "OFF"
    show_message(
        f"DynSubdiv: {sub_status}, Detail={settings.details_level}, Stretch={stretch_status}",
        3000
    )
