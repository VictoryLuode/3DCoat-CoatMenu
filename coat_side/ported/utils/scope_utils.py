"""
Scope Utilities

Provides a unified scope model for batch operations:
- CURRENT: Selected sculpt object(s) only
- TREE: Selection + all children recursively  
- OTHER: Everything EXCEPT selection subtree
- ALL: Entire sculpt tree

Design Principles:
- Use SceneAPI for all context fetching
- Pure functions that take elements as arguments
- Selection preservation is handled at the caller level
"""
from __future__ import annotations
from dataclasses import dataclass
import coat
from typing import Callable, Iterator
from enum import Enum

from ported.utils.scene_api import (
    SceneAPI,
    SelectionAPI,
    deduplicate_elements,
    get_element_path,
)


# =============================================================================
# PROGRESS CALLBACK TYPES
# =============================================================================

ProgressCallback = Callable[[int, int, str], None]
"""Progress callback: (index: int, total: int, name: str) -> None"""


@dataclass
class IterationContext:
    """Carries progress context through scope resolution and iteration.
    
    Pass this to `apply_to_scope()` or `resolve_scope()` and progress
    callbacks will fire automatically during element iteration.
    """
    # Action verb for per-element messages: "Decimating", "Voxelizing", etc.
    # Produces: "  Decimating 'Cube' (1/5)..."
    action_verb: str = "Processing"
    # Fired for each element: (index, total, element_name)
    on_progress: ProgressCallback | None = None
    # Fired once at start: message like "Decimating subtree (5 objects)..."
    on_start: Callable[[str], None] | None = None
    # Fired once on completion: message like "Decimated 5/5 objects"
    on_complete: Callable[[str], None] | None = None


# Default action verb constant
DEFAULT_ACTION_VERB: str = "Processing"


class Scope(Enum):
    """Operation scope enumeration."""
    CURRENT: str = "current"  # Selected object(s) only
    TREE: str = "tree"        # Selection + children
    OTHER: str = "other"      # Everything except selection subtree
    ALL: str = "all"          # Entire sculpt tree


# =============================================================================
# SCOPE RESOLUTION - Convert scope enum to element lists
# =============================================================================

def resolve_scope(
    scope: Scope,
    selected: list[coat.SceneElement] | None = None,
    include_hidden: bool = False,
) -> list[coat.SceneElement]:
    """
    Resolve a scope enum to a list of elements.

    Args:
        scope: The operation scope
        selected: Optional pre-fetched selection (avoids re-fetching)
        include_hidden: If True, include hidden elements (for visibility ported.ops)

    Returns:
        List of elements matching the scope
    """
    # Fetch selection if not provided
    if selected is None:
        selected = SceneAPI.get_selected_elements()

    root: coat.SceneElement | None = SceneAPI.get_sculpt_root()

    if scope == Scope.CURRENT:
        return list(selected)

    elif scope == Scope.TREE:
        return _resolve_tree_scope(selected, include_hidden)

    elif scope == Scope.OTHER:
        return _resolve_other_scope(selected, root, include_hidden)

    elif scope == Scope.ALL:
        return _resolve_all_scope(root, include_hidden)

    return []


def _resolve_tree_scope(
    selected: list[coat.SceneElement],
    include_hidden: bool = False
) -> list[coat.SceneElement]:
    """
    Resolve TREE scope: selection + all direct descendants.

    Uses custom traversal via childCount()/child(index) to avoid
    3DCoat's iterateSubtree which traverses instance links.

    WORKAROUND (3DCoat 2025): Two API bugs require special handling:
    1. collectSelected() returns ALL instances when user selects one instance
    2. iterateSubtree() and child() traverse through instance links

    We take only the FIRST selected element to avoid processing both
    original and instance (which share mesh data). This workaround may
    become unnecessary if 3DCoat API is updated to not auto-select instances.

    Args:
        selected: Currently selected elements
        include_hidden: If True, include hidden elements

    Returns:
        Selected elements plus all their direct descendants (no instance traversal)
    """
    if not selected:
        return []

    # WORKAROUND: When user selects one instance, 3DCoat returns BOTH instances.
    # We only want to process the FIRST one (the one user actually clicked).
    # Deduplicate first, then take only the first element.
    unique_selected: list[coat.SceneElement] = deduplicate_elements(selected)

    # WORKAROUND: Process only first selected element's subtree to avoid
    # processing both original and instance when they share mesh data
    first_selected: coat.SceneElement = unique_selected[0]

    # Use direct traversal - avoids instance link traversal
    tree_elements: list[coat.SceneElement] = SceneAPI.collect_subtree_direct(
        first_selected, include_hidden=include_hidden
    )

    return tree_elements


def _resolve_other_scope(
    selected: list[coat.SceneElement],
    root: coat.SceneElement | None,
    include_hidden: bool = False
) -> list[coat.SceneElement]:
    """
    Resolve OTHER scope: everything except selection subtrees.

    Args:
        selected: Currently selected elements
        root: Scene root element
        include_hidden: If True, include hidden elements

    Returns:
        All elements not in any selection subtree
    """
    if not root:
        return []

    # Build set of paths in selection trees (path-based, not id-based)
    tree_paths: set[str] = set()
    for sel in selected:
        subtree: list[coat.SceneElement] = SceneAPI.collect_subtree_direct(
            sel, include_hidden=include_hidden
        )
        for el in subtree:
            tree_paths.add(get_element_path(el))

    # Collect all elements NOT in selection trees
    all_elements: list[coat.SceneElement] = SceneAPI.collect_subtree_direct(
        root, include_hidden=include_hidden
    )
    return [el for el in all_elements if get_element_path(el) not in tree_paths]


def _resolve_all_scope(
    root: coat.SceneElement | None,
    include_hidden: bool = False
) -> list[coat.SceneElement]:
    """
    Resolve ALL scope: entire sculpt tree.

    Uses direct parent→child traversal to avoid instance link issues.

    Args:
        root: Scene root element
        include_hidden: If True, include hidden elements

    Returns:
        All elements in the scene (direct descendants only)
    """
    if not root:
        return []
    return SceneAPI.collect_subtree_direct(root, include_hidden=include_hidden)


# =============================================================================
# SCOPED OPERATIONS - Apply operations to scoped elements
# =============================================================================

def apply_to_scope(
    scope: Scope,
    operation: Callable[[coat.SceneElement], None],
    preserve_selection: bool = True,
    ctx: IterationContext | None = None,
) -> int:
    """
    Apply an operation to all elements matching the scope.

    Args:
        scope: The operation scope
        operation: Function to apply to each element
        preserve_selection: Whether to restore selection after operation
        ctx: Optional iteration context for progress callbacks

    Returns:
        Number of elements processed
    """
    # Cache selection for restoration
    original_selection: list[coat.SceneElement] = []
    if preserve_selection:
        original_selection = SelectionAPI.save_selection()

    # Resolve scope to elements
    elements: list[coat.SceneElement] = resolve_scope(
        scope, original_selection)
    total: int = len(elements)

    # Start message
    if ctx and ctx.on_start and total > 0:
        scope_name: str = scope.name.lower() if hasattr(scope, 'name') else str(scope)
        ctx.on_start(f"{ctx.action_verb} {scope_name} ({total} objects)...")

    # Apply operation
    count: int = 0
    for i, el in enumerate(elements):
        if ctx and ctx.on_progress:
            ctx.on_progress(i, total, el.name())
        operation(el)
        count += 1

    # Completion message
    if ctx and ctx.on_complete and total > 0:
        ctx.on_complete(f"{ctx.action_verb} {total}/{total} objects")

    # Restore selection
    if preserve_selection and original_selection:
        SelectionAPI.restore_selection(original_selection)

    return count


# =============================================================================
# INSTANCE-SKIP ITERATORS
# =============================================================================

class SkippedCounter:
    """Mutable counter for tracking instance-skipped elements during iteration."""
    __slots__ = ('value',)

    def __init__(self) -> None:
        self.value: int = 0


def skip_instances(
    elements: list[coat.SceneElement],
) -> tuple[list[coat.SceneElement], SkippedCounter]:
    """
    Filter out instance-duplicate elements from a batch.

    Snapshots each element's polycount before any operations. Returns
    a lazily-evaluated iterable: each element's polycount is re-checked
    against the snapshot at iteration time. When a prior element's
    modification changes a sibling's polycount (shared mesh data =
    instance), that sibling is skipped.

    Returns:
        (non_instance_elements, skipped_counter)
        non_instance_elements is iterable — instance detection happens
        during iteration, not at construction time.
        Access skipped_counter.value after iteration for the count.
    """
    _snapshots: dict[str, int] = {}
    for el in elements:
        if el.isSculptObject():
            pc: int = el.Volume().getPolycount()
            if pc > 0:
                _snapshots[el.name()] = pc

    counter: SkippedCounter = SkippedCounter()

    def _generate() -> Iterator[coat.SceneElement]:
        for el in elements:
            if el.isSculptObject() and el.name() in _snapshots:
                current_pc: int = el.Volume().getPolycount()
                snapshot_pc: int = _snapshots[el.name()]
                if current_pc != snapshot_pc:
                    print(
                        f"[skip_instances] SKIP '{el.name()}': instance — "
                        f"polycount changed from {snapshot_pc:,} to "
                        f"{current_pc:,} (shared mesh)"
                    )
                    counter.value += 1
                    continue
            yield el

    class _LazyFiltered:
        __slots__ = ('_list',)

        def _materialize(self) -> list[coat.SceneElement]:
            if not hasattr(self, '_list'):
                self._list = list(_generate())
            return self._list

        def __iter__(self) -> Iterator[coat.SceneElement]:
            return iter(self._materialize())

        def __len__(self) -> int:
            return len(self._materialize())

        def __bool__(self) -> bool:
            return len(self._materialize()) > 0

    return _LazyFiltered(), counter


def resolve_scope_skip_instances(
    scope: Scope,
    selected: list[coat.SceneElement] | None = None,
    include_hidden: bool = False,
) -> tuple[list[coat.SceneElement], SkippedCounter]:
    """
    Convenience: resolve scope then filter out instance-duplicates.

    Equivalent to calling resolve_scope() then skip_instances().

    Args:
        scope: The operation scope
        selected: Optional pre-fetched selection
        include_hidden: If True, include hidden elements

    Returns:
        (non_instance_elements, skipped_counter)
        Access skipped_counter.value after iteration for the count.
    """
    resolved: list[coat.SceneElement] = resolve_scope(
        scope, selected=selected, include_hidden=include_hidden
    )
    return skip_instances(resolved)


# =============================================================================
# DEPRECATED - Kept for backwards compatibility
# Use scene_api.py and SceneElement_visibility_utils.py for new code
# =============================================================================

def get_selected_elements() -> list[coat.SceneElement]:
    """DEPRECATED: Use SceneAPI.get_selected_elements() instead."""
    return SceneAPI.get_selected_elements()


def restore_selection(elements: list[coat.SceneElement]) -> None:
    """DEPRECATED: Use SelectionAPI.restore_selection() instead."""
    SelectionAPI.restore_selection(elements)


def get_elements_by_scope(scope: Scope) -> list[coat.SceneElement]:
    """DEPRECATED: Use resolve_scope() instead."""
    return resolve_scope(scope)


def collect_tree_elements(root: coat.SceneElement) -> list[coat.SceneElement]:
    """DEPRECATED: Use SceneAPI.collect_subtree() instead."""
    return SceneAPI.collect_subtree(root)
