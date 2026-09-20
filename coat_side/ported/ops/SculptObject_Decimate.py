"""
SculptObject_Decimate Operator

Decimate sculpt objects to reduce polygon count.
Supports: percentage reduction and target polycount.

For proxy mode (16X decimation cache), use SculptObject_Proxy instead.

Uses scope resolution to determine which elements to operate on.
"""
import coat
from dataclasses import dataclass
from typing import Callable
from ported.utils.scene_api import SceneAPI
from ported.utils.scope_utils import Scope, resolve_scope_skip_instances
from ported.utils.Volume_decimate_utils import execute_decimate
from ported.utils.Volume_mode_utils import ensure_surface_mode
from ported.utils.Scene_cleanup_utils import cleanup_after_mesh_operation
from ported.utils.coat_ui_utils import show_message, show_error

# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_REDUCTION_PERCENT: float = 50.0


# =============================================================================
# CONFIG DATACLASS
# =============================================================================

@dataclass
class DecimateConfig:
    """Configuration for decimate operation."""
    reduction_percent: float | None = DEFAULT_REDUCTION_PERCENT
    target_polycount: int | None = None


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _decimate_element(
    element: coat.SceneElement,
    config: DecimateConfig
) -> bool:
    """
    Decimate a single element.

    Returns:
        True if element was decimated, False if skipped
    """
    if not element.isSculptObject():
        return False

    vol: coat.Volume = element.Volume()
    ensure_surface_mode(vol)

    # Select element for operation
    element.selectOne()

    # Prefer the proven ReductionPercent dialog path. Absolute polycount
    # targets are converted to an equivalent removal percentage.
    polys_before: int = int(vol.getPolycount())
    exec_percent: float | None = config.reduction_percent
    exec_poly: int | None = None
    if config.target_polycount is not None:
        target: int = int(config.target_polycount)
        if polys_before <= 0:
            return False
        if target >= polys_before:
            return True
        # ReductionPercent = percent to REMOVE (50 → half the mesh).
        # At 50% remove/keep are identical; for targets we need (1 - target/current).
        exec_percent = max(
            0.01,
            min(99.99, (1.0 - (target / float(polys_before))) * 100.0),
        )

    execute_decimate(
        target_polycount=exec_poly,
        reduction_percent=exec_percent,
    )

    return True


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    reduction_percent: float | None = DEFAULT_REDUCTION_PERCENT,
    target_polycount: int | None = None,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Decimate objects to reduce polygon count.

    Args:
        scope: Which objects to decimate
        reduction_percent: Percentage of polygons to remove (e.g., 50.0 = half)
        target_polycount: Absolute target polycount (overrides percent if set)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects decimated
    """
    from ported.utils.scene_api import SelectionAPI

    # Save selection for restoration (multi-selection aware)
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validate for scope-dependent operations
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Target polycount overrides percent when both are provided
    effective_percent: float | None = (
        None if target_polycount is not None else reduction_percent
    )
    config = DecimateConfig(
        reduction_percent=effective_percent,
        target_polycount=target_polycount,
    )

    # Resolve which elements to operate on
    elements, _ = resolve_scope_skip_instances(scope)

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    total: int = len(elements)

    # Decimate each element
    count: int = 0
    for i, el in enumerate(elements):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if _decimate_element(el, config):
            count += 1

    # Cleanup after mesh operations
    cleanup_after_mesh_operation()

    # Restore selection (multi-selection aware)
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    # Build status message
    if target_polycount is not None:
        status: str = f"Decimated {count}/{total} to {target_polycount:,}"
    else:
        status = f"Decimated {count}/{total} by {reduction_percent:.0f}%"

    show_message(f"{status} objects", 2000)
    return count
