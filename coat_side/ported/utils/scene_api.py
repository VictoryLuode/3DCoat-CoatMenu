"""
Scene API - Thin wrappers around 3DCoat's native scene iteration.

This module provides static functions that return Python lists instead of
requiring callbacks. All context-fetching is localized here - other modules
should receive data as arguments rather than fetching their own context.

Design Principles:
- Wrap callback-based iterators into list-returning functions
- Provide typed return values for better IDE support
- Localize 3DCoat context operations here
- Pass data explicitly to downstream functions
"""
import coat
from typing import Callable


# =============================================================================
# SCENE ELEMENT COLLECTION
# =============================================================================

class SceneAPI:
    """
    Static API for 3DCoat scene operations.

    All methods are static - no instance state.
    This class wraps 3DCoat's callback-based iteration patterns
    into simple list-returning functions.
    """

    @staticmethod
    def get_sculpt_root() -> coat.SceneElement | None:
        """
        Get the sculpt tree root element.

        Returns:
            Root element, or None if no scene loaded
        """
        return coat.Scene.sculptRoot()

    @staticmethod
    def get_current_element() -> coat.SceneElement | None:
        """
        Get the currently selected/active element.

        Returns:
            Current element, or None if nothing selected
        """
        return coat.Scene.current()

    @staticmethod
    def get_current_volume() -> coat.Volume | None:
        """
        Get the volume of the currently selected element.

        Returns:
            Current volume, or None if no volume selected
        """
        current: coat.SceneElement | None = coat.Scene.current()
        if not current:
            return None
        return current.Volume()

    @staticmethod
    def get_selected_elements() -> list[coat.SceneElement]:
        """
        Get all currently selected sculpt elements as a list.

        WORKAROUND (3DCoat 2025): collectSelected() returns duplicates AND
        instance-linked elements when user selects a single instance.
        For example, selecting LeftLeg returns [LeftLeg, RightLeg, LeftLeg, RightLeg]
        when RightLeg is an instance of LeftLeg.
        This may be fixed in a future 3DCoat API update.

        Returns:
            List of selected SceneElement objects (deduplicated by path)
        """
        root: coat.SceneElement | None = coat.Scene.sculptRoot()
        if not root:
            return []
        raw_selected: list[coat.SceneElement] = root.collectSelected()
        # WORKAROUND: Deduplicate - collectSelected() returns duplicates and instance links
        return deduplicate_elements(raw_selected)

    @staticmethod
    def collect_subtree(
        root: coat.SceneElement,
        max_elements: int = 10000,
    ) -> list[coat.SceneElement]:
        """
        Collect all elements in a subtree (root + all visible descendants).

        Uses path-based deduplication to prevent infinite loops when
        instances or circular references exist in the scene.

        Args:
            root: Root element of the subtree
            max_elements: Safety limit to prevent runaway iteration

        Returns:
            List containing root and all visible descendants
        """
        return collect_subtree_safe(
            root, include_hidden=False, max_elements=max_elements
        )

    @staticmethod
    def collect_all_subtree(
        root: coat.SceneElement,
        max_elements: int = 10000,
    ) -> list[coat.SceneElement]:
        """
        Collect all elements in a subtree (root + ALL descendants).

        Uses path-based deduplication to prevent infinite loops when
        instances or circular references exist in the scene.

        NOTE: Uses 3DCoat's iterateSubtree which may traverse instance links.
        For mesh operations, use collect_subtree_direct() instead.

        Args:
            root: Root element of the subtree
            max_elements: Safety limit to prevent runaway iteration

        Returns:
            List containing root and all descendants
        """
        return collect_subtree_safe(
            root, include_hidden=True, max_elements=max_elements
        )

    @staticmethod
    def collect_subtree_direct(
        root: coat.SceneElement,
        include_hidden: bool = False,
        max_elements: int = 10000,
    ) -> list[coat.SceneElement]:
        """
        Collect subtree using direct parent→child traversal only.

        This is the PREFERRED method for operations that modify mesh data.
        Unlike iterateSubtree, this only follows direct parent→child links
        and will not traverse instance references.

        Args:
            root: Root element of the subtree
            include_hidden: If True, include hidden elements
            max_elements: Safety limit to prevent runaway iteration

        Returns:
            List containing root and all direct descendants (no instances)
        """
        return collect_subtree_direct(
            root, include_hidden=include_hidden, max_elements=max_elements
        )

    @staticmethod
    def collect_all_sculpt_objects(
        max_elements: int = 10000,
    ) -> list[coat.SceneElement]:
        """
        Collect all sculpt objects in the entire scene.

        Uses path-based deduplication to prevent infinite loops.

        Args:
            max_elements: Safety limit to prevent runaway iteration

        Returns:
            List of all sculpt objects (elements where isSculptObject() is True)
        """
        root: coat.SceneElement | None = coat.Scene.sculptRoot()
        if not root:
            return []

        # Use safe subtree collection
        all_elements: list[coat.SceneElement] = collect_subtree_safe(
            root, include_hidden=True, max_elements=max_elements
        )

        # Filter to sculpt objects only
        return [el for el in all_elements if el.isSculptObject()]

    @staticmethod
    def collect_visible_sculpt_objects(
        max_elements: int = 10000,
    ) -> list[coat.SceneElement]:
        """
        Collect all visible sculpt objects in the scene.

        Uses path-based deduplication to prevent infinite loops.

        Args:
            max_elements: Safety limit to prevent runaway iteration

        Returns:
            List of visible sculpt objects
        """
        root: coat.SceneElement | None = coat.Scene.sculptRoot()
        if not root:
            return []

        # Use safe subtree collection
        all_elements: list[coat.SceneElement] = collect_subtree_safe(
            root, include_hidden=False, max_elements=max_elements
        )

        # Filter to sculpt objects only
        return [el for el in all_elements if el.isSculptObject()]


# =============================================================================
# SELECTION OPERATIONS
# =============================================================================

class SelectionAPI:
    """
    Static API for selection state management.

    Provides utilities for saving and restoring selection state,
    which is important because many operations inadvertently change selection.
    """

    @staticmethod
    def save_selection() -> list[coat.SceneElement]:
        """
        Save the current selection state.

        Returns:
            List of currently selected elements (for later restoration)
        """
        return SceneAPI.get_selected_elements()

    @staticmethod
    def restore_selection(elements: list[coat.SceneElement]) -> None:
        """
        Restore selection to a previously saved state.

        Args:
            elements: List of elements to select (from save_selection)
        """
        if not elements:
            return

        # Select the first one exclusively, then add others
        elements[0].selectOne()
        for el in elements[1:]:
            el.select()

    @staticmethod
    def select_one(element: coat.SceneElement) -> None:
        """
        Select a single element exclusively (deselect all others).

        Args:
            element: Element to select
        """
        element.selectOne()

    @staticmethod
    def select_add(element: coat.SceneElement) -> None:
        """
        Add an element to the current selection.

        Args:
            element: Element to add to selection
        """
        element.select()


# =============================================================================
# ELEMENT OPERATIONS (Pure functions that take elements as args)
# =============================================================================

def apply_to_elements(
    elements: list[coat.SceneElement],
    operation: Callable[[coat.SceneElement], None]
) -> int:
    """
    Apply an operation to a list of elements.

    This is the core pattern: receive data as arguments, don't fetch context.

    Args:
        elements: List of elements to process
        operation: Function to apply to each element

    Returns:
        Number of elements processed
    """
    count: int = 0
    for el in elements:
        operation(el)
        count += 1
    return count


def filter_elements(
    elements: list[coat.SceneElement],
    predicate: Callable[[coat.SceneElement], bool]
) -> list[coat.SceneElement]:
    """
    Filter elements by a predicate function.

    Args:
        elements: List of elements to filter
        predicate: Function returning True for elements to keep

    Returns:
        Filtered list of elements
    """
    return [el for el in elements if predicate(el)]


def filter_sculpt_objects(elements: list[coat.SceneElement]) -> list[coat.SceneElement]:
    """
    Filter to only sculpt objects.

    Args:
        elements: List of elements to filter

    Returns:
        List containing only elements where isSculptObject() is True
    """
    return filter_elements(elements, lambda el: el.isSculptObject())


def get_element_ids(elements: list[coat.SceneElement]) -> set[int]:
    """
    Get Python object IDs for a list of elements (for fast set operations).

    WARNING: Python id() is unreliable for 3DCoat elements - each API call
    may return a new wrapper object with a different id(). Use path-based
    deduplication instead (deduplicate_elements_by_path).

    Args:
        elements: List of elements

    Returns:
        Set of Python object IDs
    """
    return {id(el) for el in elements}


def deduplicate_elements(elements: list[coat.SceneElement]) -> list[coat.SceneElement]:
    """
    Remove duplicate elements using path-based comparison.

    NOTE: This uses element paths, not Python id(), because 3DCoat creates
    new Python wrapper objects on each API call. Two wrappers with different
    id() values may represent the same underlying element.

    Args:
        elements: List that may contain duplicates

    Returns:
        List with duplicates removed (preserves first occurrence)
    """
    seen_paths: set[str] = set()
    unique: list[coat.SceneElement] = []
    for el in elements:
        path: str = get_element_path(el)
        if path not in seen_paths:
            seen_paths.add(path)
            unique.append(el)
    return unique


def deduplicate_elements_by_id(elements: list[coat.SceneElement]) -> list[coat.SceneElement]:
    """
    Remove duplicate elements using Python id() - UNRELIABLE for 3DCoat.

    WARNING: This is unreliable because 3DCoat creates new wrapper objects.
    Prefer deduplicate_elements() which uses path-based comparison.

    Args:
        elements: List that may contain duplicates

    Returns:
        List with duplicates removed
    """
    seen: set[int] = set()
    unique: list[coat.SceneElement] = []
    for el in elements:
        el_id: int = id(el)
        if el_id not in seen:
            seen.add(el_id)
            unique.append(el)
    return unique


# =============================================================================
# ELEMENT PATH UTILITIES
# =============================================================================

def get_element_path(element: coat.SceneElement) -> str:
    """
    Build a unique path string for an element by walking up the parent chain.

    This creates a path like "Root/Arm/Hand/Finger" that uniquely identifies
    an element's position in the scene tree. Stops at "Root" which is the
    consistent base of the sculpt tree.

    Args:
        element: SceneElement to get path for

    Returns:
        Path string from root to element
    """
    parts: list[str] = []
    current: coat.SceneElement | None = element

    # Walk up the parent chain (limit iterations for safety)
    max_depth: int = 100
    depth: int = 0

    while current is not None and depth < max_depth:
        try:
            name: str = current.name()
            if name:
                parts.append(name)
                # Stop at Root - it's the consistent base of the sculpt tree
                if name == "Root":
                    break
            # Skip unnamed elements (don't add to path)
        except Exception:
            pass  # Skip elements we can't get names for

        try:
            parent: coat.SceneElement = current.parent()
            # Check if parent is valid (not null/empty)
            if parent is None:
                break
            # Check if we've reached the root (parent == current)
            if parent == current:
                break
            current = parent
        except Exception:
            break

        depth += 1

    # Reverse to get root-to-element order
    parts.reverse()
    return "/".join(parts)


def collect_subtree_safe(
    root: coat.SceneElement,
    include_hidden: bool = False,
    max_elements: int = 10000,
) -> list[coat.SceneElement]:
    """
    Safely collect subtree elements with path-based deduplication.

    This prevents infinite loops when the scene contains instances or
    circular references by tracking visited element paths.

    NOTE: This uses 3DCoat's iterateSubtree which may traverse instance links,
    causing duplicate operations on shared data. For operations that modify
    mesh data, prefer collect_subtree_direct() which only follows parent→child
    relationships.

    Args:
        root: Root element to start from
        include_hidden: If True, include hidden elements
        max_elements: Maximum elements to collect (safety limit)

    Returns:
        List of unique elements in the subtree
    """
    elements: list[coat.SceneElement] = [root]
    visited_paths: set[str] = {get_element_path(root)}

    def collector(el: coat.SceneElement) -> bool:
        # Safety limit
        if len(elements) >= max_elements:
            return True  # Stop iteration

        # Get unique path for this element
        path: str = get_element_path(el)

        # Skip if we've already visited this path
        if path in visited_paths:
            return False  # Continue but don't add

        visited_paths.add(path)
        elements.append(el)
        return False  # Continue iteration

    if include_hidden:
        root.iterateSubtree(collector)
    else:
        root.iterateVisibleSubtree(collector)

    return elements


def collect_subtree_direct(
    root: coat.SceneElement,
    include_hidden: bool = False,
    max_elements: int = 10000,
) -> list[coat.SceneElement]:
    """
    Collect subtree using direct parent→child traversal only.

    WORKAROUND (3DCoat 2025): Two API bugs require custom traversal:
    1. iterateSubtree() traverses through instance links to unrelated branches
    2. child(index) ALSO returns instance-linked elements from other branches

    This function uses childCount() + child(index) with path-prefix filtering
    to ensure only true descendants are returned. Elements whose path doesn't
    start with root's path are filtered out.

    This workaround may become unnecessary if 3DCoat API is updated to
    properly isolate instance links during iteration.

    Uses iterative BFS to avoid Python recursion limits.

    Args:
        root: Root element to start from
        include_hidden: If True, include hidden elements
        max_elements: Maximum elements to collect (safety limit)

    Returns:
        List of unique elements in the subtree (direct descendants only)
    """
    # Get the root path - all valid children must have paths starting with this
    root_path: str = get_element_path(root)

    elements: list[coat.SceneElement] = []
    queue: list[coat.SceneElement] = [root]
    visited_paths: set[str] = set()

    while queue and len(elements) < max_elements:
        current: coat.SceneElement = queue.pop(0)

        # Get path for deduplication and ancestry check
        path: str = get_element_path(current)

        # Skip if already visited
        if path in visited_paths:
            continue
        visited_paths.add(path)

        # CRITICAL: Only include elements whose path starts with root path
        # This filters out instance-linked elements that child() may return
        if not path.startswith(root_path):
            continue

        # Check visibility if required
        if not include_hidden:
            try:
                if not current.visible():
                    continue
            except Exception:
                pass  # If we can't check visibility, include it

        elements.append(current)

        # Add direct children to queue using childCount() + child(index)
        try:
            child_count: int = current.childCount()
            for i in range(child_count):
                try:
                    child: coat.SceneElement = current.child(i)
                    if child is not None:
                        queue.append(child)
                except Exception:
                    pass  # Skip children we can't access
        except Exception:
            pass  # Skip if we can't get child count

    return elements


# =============================================================================
# VOLUME OBJECT IDENTITY (Instance Detection)
# =============================================================================

def is_same_volume(a: coat.SceneElement, b: coat.SceneElement) -> bool:
    """
    Check if two elements share the same VolumeObject (shared mesh / instance).

    Shared VO means shared **mesh data**, not a shared scene-graph transform.
    Each instance still has its own ``getTransform()`` / ``setTransform()``.
    Use this for mesh ported.ops that mutate volume content; do **not** use it to
    skip transform updates (see scale tooling).

    Compare with ``va.vo() == vb.vo()`` while both wrappers are alive.
    Never use ``id(vo)`` — wrappers are ephemeral and ids recycle.

    Args:
        a: First element to compare
        b: Second element to compare

    Returns:
        True if both elements reference the same VolumeObject
    """
    try:
        va: coat.Volume | None = a.Volume()
        vb: coat.Volume | None = b.Volume()
        if va and vb:
            return va.vo() == vb.vo()
    except Exception:
        pass
    return False


def deduplicate_elements_by_vo(
    elements: list[coat.SceneElement],
) -> list[coat.SceneElement]:
    """
    Keep one SceneElement per unique VolumeObject (shared mesh).

    Intended for **mesh** operations where mutating one VO updates all
    instances. Do **not** use before transform/scale — instances need their
    own ``setTransform`` (they do not inherit the source's transform).

    Never key identity with Python ``id(vo)``. ``Volume.vo()`` returns
    ephemeral wrappers; recycled ``id()`` values falsely collide unrelated
    parts. Keep wrappers alive and compare with ``==``.

    Args:
        elements: List that may contain instance-linked duplicates

    Returns:
        List with only one element per unique VolumeObject
    """
    # Keep wrappers alive for the duration of this pass so ``==`` is stable.
    seen_vos: list[object] = []
    result: list[coat.SceneElement] = []
    for el in elements:
        try:
            vol: coat.Volume | None = el.Volume()
            if vol:
                vo: object | None = vol.vo()
                if vo is not None:
                    already_seen: bool = False
                    for seen in seen_vos:
                        if vo == seen:
                            already_seen = True
                            break
                    if already_seen:
                        continue
                    seen_vos.append(vo)
        except Exception:
            pass
        result.append(el)
    return result
