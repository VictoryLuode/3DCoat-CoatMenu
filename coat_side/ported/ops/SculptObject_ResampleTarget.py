"""
SculptObject_ResampleTarget Operator

Resample sculpt objects to a target polycount or target world-space density.

Two modes:
- TARGET_POLYCOUNT: Resample each element to an absolute polygon count,
  regardless of object size.  Use to set a uniform polycount across objects.
- TARGET_DENSITY: Resample each element to a uniform world-space detail
  level.  Larger objects get proportionally more polygons so detail
  density stays consistent.  Use to match voxel size across a scene.

Every step is instrumented with console print diagnostics so you can
compare intent to outcome inside 3DCoat's Script Editor / console log.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from enum import Enum
from typing import Callable

from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances, SkippedCounter
from ported.utils.Volume_resample_utils import execute_resample_scale_only
from ported.utils.Scene_cleanup_utils import cleanup_after_mesh_operation
from ported.utils.coat_ui_utils import show_message, show_error, wait_frames


# =============================================================================
# MODE ENUM
# =============================================================================

class ResampleTargetMode(Enum):
    """Resample targeting strategy."""
    TARGET_POLYCOUNT: str = "target_polycount"
    TARGET_DENSITY: str = "target_density"


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_POLYCOUNT: int = 10000
DEFAULT_DENSITY: float = 100.0
TOLERANCE: float = 0.05

# How many frames to wait before reading back the post-op polycount
VERIFY_WAIT_FRAMES: int = 2


# =============================================================================
# DIAGNOSTIC HELPERS
# =============================================================================

_SEPARATOR: str = "-" * 60


def _log_header(element_name: str, mode: str) -> None:
    print(f"\n{_SEPARATOR}")
    print(f"[ResampleTarget] Element: '{element_name}' | Mode: {mode}")
    print(_SEPARATOR)


def _log_footer(
    name: str,
    before: int,
    expected: int,
    after: int,
    action: str,
) -> None:
    delta_pct: float = ((after - expected) / expected * 100.0
                        if expected > 0 else 0.0)
    print(
        f"[ResampleTarget] RESULT '{name}': "
        f"before={before:,}  target={expected:,}  after={after:,}  "
        f"delta={delta_pct:+.1f}%  action={action}"
    )
    print(_SEPARATOR)


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _resample_to_polycount(
    element: coat.SceneElement,
    target_polycount: int,
) -> bool:
    """
    Resample a single element to an absolute target polycount.

    Sends mathematically consistent polycount and scale (scale =
    target/current) so both dialog fields agree and 3DCoat has
    nothing to reconcile — the operation converges to the target.

    Returns:
        True if element was resampled, False if skipped
    """
    name: str = element.name()
    _log_header(name, "TARGET_POLYCOUNT")

    if not element.isSculptObject():
        print(f"[ResampleTarget]   SKIP: not a SculptObject")
        return False

    vol: coat.Volume = element.Volume()

    element.selectOne()

    current: int = vol.getPolycount()
    print(f"[ResampleTarget]   current polycount = {current:,}")

    if current <= 0:
        print(f"[ResampleTarget]   SKIP: zero polycount")
        return False

    ratio: float = target_polycount / current
    print(
        f"[ResampleTarget]   current = {current:,}  "
        f"target = {target_polycount:,}  ratio = {ratio:.4f}"
    )

    # Early-out: skip if already within tolerance
    if (1.0 - TOLERANCE) < ratio < (1.0 + TOLERANCE):
        print(
            f"[ResampleTarget]   SKIP: within {TOLERANCE*100:.0f}% "
            f"of target (ratio {ratio:.4f})"
        )
        return True  # counts as "processed" but skipped the op

    execute_resample_scale_only(ratio=ratio)

    # ── Post-op verification ──
    wait_frames(VERIFY_WAIT_FRAMES)
    after: int = vol.getPolycount()
    _log_footer(name, current, target_polycount, after, "resampled")
    return True


def _resample_to_density(
    element: coat.SceneElement,
    target_density: float,
) -> bool:
    """
    Resample a single element to a uniform world-space detail density.

    Calculates target polycount from the element's world-space bounding box
    and the specified density value (tris per unit²).  Larger objects get
    proportionally more polygons to maintain consistent detail.

    Sends mathematically consistent polycount and scale so both dialog
    fields agree — the operation converges to the target.

    Formula: target_polycount = target_density × avg_dim²
    where avg_dim is the average of the bounding box X, Y, Z dimensions.

    Args:
        element: The SceneElement to resample
        target_density: Desired tris per world-unit² (a 1-unit object gets
            approximately this many polygons)

    Returns:
        True if element was resampled, False if skipped
    """
    name: str = element.name()
    _log_header(name, "TARGET_DENSITY")

    if not element.isSculptObject():
        print(f"[ResampleTarget]   SKIP: not a SculptObject")
        return False

    vol: coat.Volume = element.Volume()

    element.selectOne()

    current: int = vol.getPolycount()
    print(f"[ResampleTarget]   current polycount = {current:,}")

    if current <= 0:
        print(f"[ResampleTarget]   SKIP: zero polycount")
        return False

    # ── World-space bounding box ──
    aabb: coat.boundbox = vol.calcWorldSpaceAABB()
    size: coat.vec3 = aabb.GetSize()
    avg_dim: float = (size.x + size.y + size.z) / 3.0

    print(
        f"[ResampleTarget]   AABB size: x={size.x:.4f}  y={size.y:.4f}  "
        f"z={size.z:.4f}  avg_dim={avg_dim:.4f}"
    )

    if avg_dim <= 0.0:
        print(f"[ResampleTarget]   SKIP: zero or negative avg_dim")
        return False

    # ── Calculate target polycount from density ──
    target_polycount: int = int(target_density * avg_dim * avg_dim)

    print(
        f"[ResampleTarget]   density={target_density:,.0f} tris/unit²  "
        f"avg_dim={avg_dim:.4f}  avg_dim²={avg_dim*avg_dim:.6f}  "
        f"→ target_polycount={target_polycount:,}"
    )

    if target_polycount <= 0:
        print(f"[ResampleTarget]   SKIP: target_polycount <= 0 "
              f"(object is too small at density {target_density:,.0f})")
        return False

    ratio: float = target_polycount / current
    print(
        f"[ResampleTarget]   ratio = {ratio:.4f}"
    )

    # Early-out: skip if already within tolerance
    if (1.0 - TOLERANCE) < ratio < (1.0 + TOLERANCE):
        print(
            f"[ResampleTarget]   SKIP: within {TOLERANCE*100:.0f}% "
            f"of target density (ratio {ratio:.4f})"
        )
        return True  # counts as "processed" but skipped the op

    execute_resample_scale_only(ratio=ratio)

    # ── Post-op verification ──
    wait_frames(VERIFY_WAIT_FRAMES)
    after: int = vol.getPolycount()
    _log_footer(name, current, target_polycount, after, "resampled")
    return True


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    target_polycount: int = DEFAULT_POLYCOUNT,
    target_density: float = DEFAULT_DENSITY,
    mode: ResampleTargetMode = ResampleTargetMode.TARGET_POLYCOUNT,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Resample objects to a target polycount or uniform density.

    Args:
        scope: Which objects to resample (CURRENT, TREE, OTHER, ALL)
        target_polycount: Absolute target polycount (used when
            mode=TARGET_POLYCOUNT)
        target_density: Target tris per world-unit² (used when
            mode=TARGET_DENSITY).  A 1-unit object receives approximately
            this many polygons; larger objects scale accordingly.
        mode: Resampling strategy
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects resampled
    """
    # ── Operation banner ──
    mode_label: str = (
        f"POLYCOUNT={target_polycount:,}"
        if mode == ResampleTargetMode.TARGET_POLYCOUNT
        else f"DENSITY={target_density:,.0f} tris/unit²"
    )
    print(f"\n{'='*60}")
    print(f"  ResampleTarget: scope={scope.name}  mode={mode_label}")
    print(f"{'='*60}")

    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validate: CURRENT and TREE scopes require a selection
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Resolve elements with instance-skip filtering
    elements: list[coat.SceneElement]
    elements, skipped_counter = resolve_scope_skip_instances(scope)

    print(f"[ResampleTarget] Resolved elements for scope={scope.name} (via skip_instances)")

    total: int = len(elements)

    # Resample each element
    count: int = 0
    skipped: int = 0
    for i, el in enumerate(elements):

        if progress_callback is not None:
            progress_callback(i, total, el.name())

        ok: bool = False
        if mode == ResampleTargetMode.TARGET_POLYCOUNT:
            ok = _resample_to_polycount(el, target_polycount)
        elif mode == ResampleTargetMode.TARGET_DENSITY:
            ok = _resample_to_density(el, target_density)

        if ok:
            count += 1
        else:
            skipped += 1

    # Cleanup after mesh operations
    cleanup_after_mesh_operation()

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    # ── Final summary ──
    print(
        f"[ResampleTarget] DONE: {count} processed, "
        f"{skipped_counter.value} instance, {skipped} skipped, "
        f"scope={scope.name}"
    )
    print("=" * 60)

    # Build status message
    if count == 0:
        show_error("No objects were resampled", 2000)
        return 0

    if mode == ResampleTargetMode.TARGET_POLYCOUNT:
        status: str = (
            f"Resampled {count} objects to {target_polycount:,} polys"
        )
    else:
        status = (
            f"Resampled {count} objects to density "
            f"{target_density:,.0f} tris/unit²"
        )

    show_message(status, 2000)
    return count


def _element_kind(el: coat.SceneElement) -> str:
    """Return a one-word label for the element type (for debug printing)."""
    try:
        if not el.isSculptObject():
            return "non-sculpt"
        vol: coat.Volume = el.Volume()
        if vol.isVoxelized():
            return "voxel"
        if vol.isSurface():
            return "surface"
        return "volume"
    except Exception:
        return "unknown"
