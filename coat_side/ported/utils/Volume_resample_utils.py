"""
Volume Resample Utilities - Resample operations on Volumes.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Operators in `_ops/` own Config dataclasses and call these functions.

GOTCHA: 3DCoat's $Resample dialog treats the scale slider as a LINEAR-
DIMENSION multiplier.  Polycount scales with area (~dimension^2), so
the result is always ``after = current * slider_value^2``.

To get ``after = current * ratio``, we pass ``slider_value = sqrt(ratio)``.
This is done inside ``execute_resample_scale_only()`` — callers pass the
desired polycount ratio and never need to think about the squaring.
"""
import coat
import math
from typing import Callable

from ported.utils.coat_ui_utils import CMD_DIALOG_OK, wait_frames

# =============================================================================
# MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

CMD_RESAMPLE: str = "$Resample"
SETTING_RESAMPLE_POLYCOUNT: str = "$ResampleParams::RequiredPolycount"
SETTING_RESAMPLE_SCALE: str = "$ResampleParams::ResamplingScale"

# =============================================================================
# DEFAULTS
# =============================================================================

MESH_OP_WAIT_FRAMES: int = 2

# =============================================================================
# NO-OP GUARD -- 3DCoat ignores scale~1.0, nudge slightly
# =============================================================================

_NOOP_ZONE_MIN: float = 0.98
_NOOP_ZONE_MAX: float = 1.02
_NOOP_NUDGE: float = 1.02


def _avoid_noop(value: float) -> float:
    """Nudge away from 1.0 to avoid 3DCoat skipping the operation."""
    if _NOOP_ZONE_MIN < value < _NOOP_ZONE_MAX:
        return _NOOP_NUDGE if value >= 1.0 else _NOOP_ZONE_MIN
    return value


# =============================================================================
# CONFIGURATOR (returns closure with raw args captured)
# =============================================================================

def _configure_dialog(slider_value: float) -> Callable[[], None]:
    """Set only the scale slider, then click OK."""

    def configurator() -> None:
        scale_ok: bool = coat.ui.setSliderValue(
            SETTING_RESAMPLE_SCALE, slider_value
        )

        print(
            f"[ResampleDialog] SCALE-ONLY: "
            f"setSliderValue(scale={slider_value:.4f}) "
            f"-> {'OK' if scale_ok else 'FAILED'}"
        )

        coat.ui.cmd(CMD_DIALOG_OK)
    return configurator


# =============================================================================
# EXECUTE FUNCTIONS (raw args)
# =============================================================================

def execute_resample_scale_only(ratio: float) -> None:
    """
    Execute resample by setting ONLY the scale slider.

    3DCoat squares the slider value (linear-dimension -> area scaling),
    so we pass ``sqrt(ratio)`` to compensate.  The caller passes the
    DESIRED polycount ratio (target / current).

    Result: ``after = current * sqrt(ratio)^2 = current * ratio``.

    Preserves voxel/surface mode — 3DCoat's $Resample always converts
    to surface, so we save the original mode and restore it after the
    operation completes.

    Args:
        ratio: Desired polycount ratio (e.g. 0.5 for half, 2.0 for double)
    """
    slider: float = math.sqrt(ratio)
    safe_slider: float = _avoid_noop(slider)
    nudge_note: str = (
        f" (nudged from sqrt={slider:.4f})" if safe_slider != slider else ""
    )
    print(
        f"[ResampleDialog] ratio={ratio:.4f} -> "
        f"slider=sqrt={safe_slider:.4f}{nudge_note}"
    )

    # Save original mode — $Resample always converts to surface
    scene: coat.Scene = coat.Scene.current()
    vol: coat.Volume = scene.Volume()
    was_voxelized: bool = vol.isVoxelized()
    print(
        f"[ResampleDialog] original mode: "
        f"{'voxel' if was_voxelized else 'surface'}"
    )

    callback: Callable[[], None] = _configure_dialog(safe_slider)
    coat.ui.cmd(CMD_RESAMPLE, callback)
    wait_frames(MESH_OP_WAIT_FRAMES)

    # Restore voxel mode if the volume was originally voxelized
    if was_voxelized:
        print("[ResampleDialog] restoring voxel mode after resample")
        vol.toVoxels()
        wait_frames(MESH_OP_WAIT_FRAMES)


# =============================================================================
# CONVENIENCE FUNCTIONS (thin wrappers with raw args)
# =============================================================================

def resample_to_half(current_polycount: int) -> None:
    """Resample current Volume to half polycount."""
    execute_resample_scale_only(ratio=0.5)


def resample_to_target(initial_polycount: int, target_polycount: int) -> None:
    """
    Resample current Volume from initial to target polycount.

    Passes target/initial to execute_resample_scale_only, which
    internally computes sqrt for the dialog slider.
    """
    ratio: float = target_polycount / initial_polycount
    execute_resample_scale_only(ratio=ratio)
    print(
        f"Resampled: {initial_polycount:,} -> {target_polycount:,} "
        f"(ratio: {ratio:.3f})"
    )
