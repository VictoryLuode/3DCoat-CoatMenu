"""
Volume Decimate Utilities - Decimate operations on Volumes.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Operators in `_ops/` own Config dataclasses and call these functions.
"""
import coat
from typing import Callable

from ported.utils.coat_ui_utils import CMD_DIALOG_OK, wait_frames

# =============================================================================
# MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

CMD_DECIMATE: str = "$Decimate"
SETTING_DECIMATE_POLYCOUNT: str = "$DecimationParams::ReducedPolycount"
SETTING_DECIMATE_PERCENT: str = "$DecimationParams::ReductionPercent"

# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_REDUCTION_PERCENT: float = 50.0
MESH_OP_WAIT_FRAMES: int = 2


# =============================================================================
# CONFIGURATOR (returns closure with raw args captured)
# =============================================================================

def configure_decimate_dialog(
    target_polycount: int | None = None,
    reduction_percent: float | None = None,
) -> Callable[[], None]:
    """
    Create a callback to configure the decimate dialog.

    Args:
        target_polycount: Absolute target polycount (if provided)
        reduction_percent: Percentage to reduce by (if provided)

    Returns:
        Closure that configures dialog and clicks OK
    """
    def configurator() -> None:
        if target_polycount is not None:
            coat.ui.setEditBoxValue(
                SETTING_DECIMATE_POLYCOUNT, target_polycount)
        if reduction_percent is not None:
            coat.ui.setSliderValue(
                SETTING_DECIMATE_PERCENT, reduction_percent)
        coat.ui.cmd(CMD_DIALOG_OK)
    return configurator


# =============================================================================
# EXECUTE FUNCTIONS (raw args)
# =============================================================================

def execute_decimate(
    target_polycount: int | None = None,
    reduction_percent: float | None = None,
) -> None:
    """
    Execute decimate on current Volume.

    Args:
        target_polycount: Absolute target polycount (if provided)
        reduction_percent: Percentage to reduce by (if provided)
    """
    callback: Callable[[], None] = configure_decimate_dialog(
        target_polycount=target_polycount,
        reduction_percent=reduction_percent,
    )
    coat.ui.cmd(CMD_DECIMATE, callback)
    wait_frames(MESH_OP_WAIT_FRAMES)


# =============================================================================
# CONVENIENCE FUNCTIONS (thin wrappers with raw args)
# =============================================================================

def decimate_by_percent(percent: float = DEFAULT_REDUCTION_PERCENT) -> None:
    """Decimate current Volume by percentage reduction."""
    execute_decimate(reduction_percent=percent)


def decimate_to_target(polycount: int) -> None:
    """Decimate current Volume to target polycount."""
    execute_decimate(target_polycount=polycount)


def decimate_to_half() -> None:
    """Decimate current Volume to approximately half (50% reduction)."""
    decimate_by_percent(50.0)
