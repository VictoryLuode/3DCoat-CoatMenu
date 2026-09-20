"""
SculptObject_Scale Operator

Scale sculpt objects by a multiplier factor about a shared pivot.
Uses scope resolution to determine which elements to operate on.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable

import coat

from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope
from ported.utils.object_utils import scale_elements_about_pivot
from ported.utils.coat_ui_utils import show_message, show_error


# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_SCALE_FACTOR: float = 1.0


class ScalePivot(str, Enum):
    """Pivot used as the scale origin (same space as element translations)."""

    WORLD_ORIGIN = "world_origin"
    SELECTION = "selection"


DEFAULT_SCALE_PIVOT: ScalePivot = ScalePivot.WORLD_ORIGIN


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    scale_factor: float = DEFAULT_SCALE_FACTOR,
    pivot: ScalePivot = DEFAULT_SCALE_PIVOT,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    verbose_log: Callable[[str], None] | None = None,
) -> int:
    """
    Scale objects by a multiplier factor about a shared pivot.

    Every sculpt object in the resolved scope is scaled (TREE = selection
    subtree). Each element's own transform is scaled in place about the pivot
    — no parent-world inverse rewrite (that caused ``S**depth`` collapse on
    deep nodes like finger tips). Flip/mirror is preserved via 3x3 multiply.

    Args:
        scope: Which objects to scale
        scale_factor: Multiplier (e.g., 0.01 = 1/100, 100.0 = 100x)
        pivot: Scale origin (world origin or selection translation)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging
        verbose_log: Optional function to log detailed per-element transform data

    Returns:
        Number of objects scaled
    """
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    elements: list[coat.SceneElement] = resolve_scope(scope)
    if not elements:
        show_error("No objects to process", 2000)
        return 0

    scale_pivot: coat.vec3
    pivot_label: str
    if pivot == ScalePivot.SELECTION:
        if not current:
            show_error("No object selected for pivot", 2000)
            return 0
        scale_pivot = current.getTransform().GetTranslation()
        pivot_label = f"selection '{current.name()}'"
    else:
        scale_pivot = coat.vec3(0.0, 0.0, 0.0)
        pivot_label = "world origin"

    sculpt_count: int = sum(1 for el in elements if el.isSculptObject())
    if sculpt_count == 0:
        show_error("No objects to process", 2000)
        return 0

    if verbose_log is not None:
        verbose_log(
            f"Scale {scale_factor}x — pivot: {pivot_label} "
            f"({scale_pivot.x:.4f}, {scale_pivot.y:.4f}, {scale_pivot.z:.4f}) — "
            f"{sculpt_count} elements"
        )

    count: int = scale_elements_about_pivot(
        elements,
        scale_factor,
        scale_pivot,
        verbose_log=verbose_log,
        progress_callback=progress_callback,
    )

    if verbose_log is not None:
        verbose_log(f"Scale {scale_factor}x — DONE ({count} scaled)")

    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    if scale_factor < 1.0:
        factor_str: str = f"1/{int(1.0 / scale_factor)}"
    else:
        factor_str = f"{int(scale_factor)}x"

    show_message(f"Scaled {count} objects by {factor_str}", 2000)
    return count
