"""
Brush Settings Utilities - Dynamic subdivision settings for all brush types.

Provides dataclasses and functions to apply auto_subdivide, details_level, 
and remove_stretching settings across all 3DCoat brush types.

Pattern:
    params = BrushDynamicSubdivParams(auto_subdivide=True, details_level=2.0)
    apply_brush_settings(params)
"""
import coat
from dataclasses import dataclass
from typing import Callable

# =============================================================================
# BRUSH TYPE LIST
# =============================================================================

BRUSH_TYPES: list[str] = [
    "carve", "flatten", "clay", "build", "draw", "smooth",
    "pinch", "inflate", "layer", "shift", "scrape", "fill",
    "growclay", "claytubes", "dam", "crease", "cut", "cutoff",
    "voxhide", "pose", "snake", "muscules", "twist", "move",
    "rapid", "polish", "brush3d", "chisel", "planar", "hpolish",
    "sweep", "caps", "reconstruct", "measure"
]

# =============================================================================
# BRUSH MAGIC UI STRINGS
# =============================================================================

# Per-brush-type settings use format: $BrushConstructor::SETTING[BRUSH_TYPE]
SETTING_AUTO_SUBDIVIDE_TEMPLATE: str = "$BrushConstructor::AutoSubdivide[{brush}]"
SETTING_DETAILS_LEVEL_TEMPLATE: str = "$BrushConstructor::DetailsLevel[{brush}]"
SETTING_REMOVE_STRETCHING_TEMPLATE: str = "$BrushConstructor::RemoveStretching[{brush}]"

# Current brush settings (without [brushtype] suffix - applies to active brush)
SETTING_AUTO_SUBDIVIDE_CURRENT: str = "$BrushConstructor::AutoSubdivide"
SETTING_DETAILS_LEVEL_CURRENT: str = "$BrushConstructor::DetailsLevel"
SETTING_REMOVE_STRETCHING_CURRENT: str = "$BrushConstructor::RemoveStretching"

# Global settings (must be enabled for per-brush settings to work)
SETTING_GLOBAL_REMOVE_STRETCHING: str = "$RemoveStretching"

# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_AUTO_SUBDIVIDE: bool = True
DEFAULT_DETAILS_LEVEL: float = 1.0
DEFAULT_REMOVE_STRETCHING: bool = True

# Range limits (floor only — no upper max on details level)
MIN_DETAILS_LEVEL: float = -1.0

# Frames to wait after enabling AutoSubdivide before DetailsLevel is writable.
# Same pattern as Autopo voxelize polycount (conditional UI field).
AUTO_SUBDIVIDE_UI_SETTLE_FRAMES: int = 2


# =============================================================================
# BRUSH SETTINGS DATACLASS
# =============================================================================

@dataclass
class BrushDynamicSubdivParams:
    """
    Parameters for dynamic subdivision brush settings.

    These settings control how brushes automatically add/remove geometry
    while sculpting.
    """
    auto_subdivide: bool = DEFAULT_AUTO_SUBDIVIDE
    details_level: float = DEFAULT_DETAILS_LEVEL
    remove_stretching: bool = DEFAULT_REMOVE_STRETCHING


# =============================================================================
# APPLY FUNCTIONS
# =============================================================================

def apply_brush_settings(params: BrushDynamicSubdivParams) -> None:
    """
    Apply dynamic subdiv settings to ALL brush types.

    Args:
        params: BrushDynamicSubdivParams with all settings
    """
    apply_auto_subdivide_all(params.auto_subdivide)
    apply_details_level_all(params.details_level)
    apply_remove_stretching_all(params.remove_stretching)


def apply_auto_subdivide_all(enabled: bool) -> None:
    """
    Set auto subdivide on all brush types.

    Args:
        enabled: Whether to enable auto subdivide
    """
    for brush_type in BRUSH_TYPES:
        setting: str = SETTING_AUTO_SUBDIVIDE_TEMPLATE.format(brush=brush_type)
        coat.ui.setBoolValue(setting, enabled)


def apply_details_level_all(level: float) -> None:
    """
    Set details level on all brush types.

    Args:
        level: Detail level (0 = neutral, higher = finer)
    """
    clamped_level: float = max(MIN_DETAILS_LEVEL, level)

    for brush_type in BRUSH_TYPES:
        setting: str = SETTING_DETAILS_LEVEL_TEMPLATE.format(brush=brush_type)
        coat.ui.setSliderValue(setting, clamped_level)


def apply_remove_stretching_all(enabled: bool) -> None:
    """
    Set remove stretching globally and on all brush types.

    Note: The global setting must be enabled for per-brush-type 
    settings to take effect.

    Args:
        enabled: Whether to enable remove stretching
    """
    # Set the global setting (required for it to work)
    coat.ui.setBoolValue(SETTING_GLOBAL_REMOVE_STRETCHING, enabled)

    # Also set per-brush-type
    for brush_type in BRUSH_TYPES:
        setting: str = SETTING_REMOVE_STRETCHING_TEMPLATE.format(
            brush=brush_type)
        coat.ui.setBoolValue(setting, enabled)


# =============================================================================
# SINGLE BRUSH FUNCTIONS
# =============================================================================

def apply_auto_subdivide(brush_type: str, enabled: bool) -> None:
    """Set auto subdivide for a specific brush type."""
    setting: str = SETTING_AUTO_SUBDIVIDE_TEMPLATE.format(brush=brush_type)
    coat.ui.setBoolValue(setting, enabled)


def apply_details_level(brush_type: str, level: float) -> None:
    """Set details level for a specific brush type."""
    setting: str = SETTING_DETAILS_LEVEL_TEMPLATE.format(brush=brush_type)
    coat.ui.setSliderValue(setting, float(level))


def apply_remove_stretching(brush_type: str, enabled: bool) -> None:
    """Set remove stretching for a specific brush type."""
    setting: str = SETTING_REMOVE_STRETCHING_TEMPLATE.format(brush=brush_type)
    coat.ui.setBoolValue(setting, enabled)


# =============================================================================
# CURRENT BRUSH FUNCTIONS (applies to active brush only - fast)
# =============================================================================

def _is_auto_subdivide_current_enabled() -> bool:
    """Read live AutoSubdivide for the active brush (False if unreadable)."""
    try:
        return bool(coat.ui.getBool(SETTING_AUTO_SUBDIVIDE_CURRENT))
    except Exception:
        try:
            return bool(coat.ui.getBoolField(SETTING_AUTO_SUBDIVIDE_CURRENT))
        except Exception:
            return False


def apply_auto_subdivide_current(enabled: bool) -> None:
    """Set auto subdivide for the currently active brush only."""
    coat.ui.setBoolValue(SETTING_AUTO_SUBDIVIDE_CURRENT, enabled)


def apply_details_level_current(level: float) -> bool:
    """
    Set details level for the currently active brush only.

    `$BrushConstructor::DetailsLevel` is a conditional UI field — it is only
    writable after AutoSubdivide is enabled and the brush UI has settled.
    After a brush switch where AutoSubdivide was off, a same-frame write
    silently fails and the visible number stays stale until a second press.

    Returns:
        True if setSliderValue reported success on the final attempt.
    """
    clamped_level: float = max(MIN_DETAILS_LEVEL, float(level))

    was_enabled: bool = _is_auto_subdivide_current_enabled()
    coat.ui.setBoolValue(SETTING_AUTO_SUBDIVIDE_CURRENT, True)
    if not was_enabled:
        coat.io.step(AUTO_SUBDIVIDE_UI_SETTLE_FRAMES)

    ok: bool = bool(
        coat.ui.setSliderValue(SETTING_DETAILS_LEVEL_CURRENT, clamped_level)
    )
    if not ok:
        coat.io.step(AUTO_SUBDIVIDE_UI_SETTLE_FRAMES)
        ok = bool(
            coat.ui.setSliderValue(SETTING_DETAILS_LEVEL_CURRENT, clamped_level)
        )
    return ok


def apply_remove_stretching_current(enabled: bool) -> None:
    """Set remove stretching for the currently active brush only."""
    coat.ui.setBoolValue(SETTING_REMOVE_STRETCHING_CURRENT, enabled)


def apply_brush_settings_current(params: BrushDynamicSubdivParams) -> None:
    """
    Apply dynamic subdiv settings to the CURRENT brush only (fast).

    Args:
        params: BrushDynamicSubdivParams with all settings
    """
    if params.auto_subdivide:
        # Hardened path: enable AutoSubdivide, settle UI, then set DetailsLevel
        apply_details_level_current(params.details_level)
    else:
        apply_auto_subdivide_current(False)
        clamped_level: float = max(MIN_DETAILS_LEVEL, float(params.details_level))
        coat.ui.setSliderValue(SETTING_DETAILS_LEVEL_CURRENT, clamped_level)
    apply_remove_stretching_current(params.remove_stretching)


# =============================================================================
# LEGACY CLASS (for backward compatibility)
# =============================================================================

class BrushSettingsUtils:
    """
    Legacy static utility class - prefer using dataclass pattern directly.

    Deprecated: Use BrushDynamicSubdivParams and apply_brush_settings() instead.
    """

    @staticmethod
    def apply_global_brush_settings(
        auto_subdivide: bool,
        details_level: float,
        remove_stretching: bool
    ) -> None:
        """Deprecated: Use apply_brush_settings(BrushDynamicSubdivParams(...))."""
        params = BrushDynamicSubdivParams(
            auto_subdivide=auto_subdivide,
            details_level=details_level,
            remove_stretching=remove_stretching
        )
        apply_brush_settings(params)

    @staticmethod
    def set_auto_subdivide_all(enabled: bool) -> None:
        """Deprecated: Use apply_auto_subdivide_all(enabled)."""
        apply_auto_subdivide_all(enabled)

    @staticmethod
    def set_details_level_all(level: float) -> None:
        """Deprecated: Use apply_details_level_all(level)."""
        apply_details_level_all(level)

    @staticmethod
    def set_remove_stretching_all(enabled: bool) -> None:
        """Deprecated: Use apply_remove_stretching_all(enabled)."""
        apply_remove_stretching_all(enabled)

    @staticmethod
    def set_auto_subdivide(brush_type: str, enabled: bool) -> None:
        """Deprecated: Use apply_auto_subdivide(brush_type, enabled)."""
        apply_auto_subdivide(brush_type, enabled)

    @staticmethod
    def set_details_level(brush_type: str, level: float) -> None:
        """Deprecated: Use apply_details_level(brush_type, level)."""
        apply_details_level(brush_type, level)

    @staticmethod
    def set_remove_stretching(brush_type: str, enabled: bool) -> None:
        """Deprecated: Use apply_remove_stretching(brush_type, enabled)."""
        apply_remove_stretching(brush_type, enabled)
