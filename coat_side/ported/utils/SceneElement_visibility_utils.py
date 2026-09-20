"""
Visibility Utilities

Pure functions for manipulating visibility and ghost state of scene elements.
All functions receive elements as arguments - no context fetching.

Design Principles:
- Functions take element lists as arguments
- No coat.Scene calls inside these functions
- Return counts for feedback
"""
import coat
from typing import Callable


# =============================================================================
# PRIVATE UTILITIES
# =============================================================================

def _element_in_list(el: coat.SceneElement, elements: list[coat.SceneElement]) -> bool:
    """
    Check if element is in list using 3DCoat's equality operator.

    Note: We use explicit loop with __eq__ because Python set/dict would use
    id() or __hash__ which may not work correctly for 3DCoat wrapper objects.

    Args:
        el: Element to check
        elements: List to check against

    Returns:
        True if element is in list (via __eq__)
    """
    for other in elements:
        if el == other:
            return True
    return False


# =============================================================================
# PARENT CHAIN UTILITIES
# =============================================================================

def collect_parent_chain(element: coat.SceneElement) -> list[coat.SceneElement]:
    """
    Collect all parent elements of an element up to the root.

    Args:
        element: Element to get parents for

    Returns:
        List of parent elements (not including the element itself)

    Note:
        SceneElement.parent() returns SceneElement (not None), so we compare
        to sculptRoot to detect when we've reached the top. A max iteration
        limit prevents infinite loops in edge cases.
    """
    parents: list[coat.SceneElement] = []
    sculpt_root: coat.SceneElement = coat.Scene.sculptRoot()
    current: coat.SceneElement = element.parent()

    # Safety limit to prevent infinite loops (scene trees rarely exceed 100 levels)
    max_iterations: int = 100
    iterations: int = 0

    while iterations < max_iterations:
        # Stop if we've reached the sculpt root (top of tree)
        if current == sculpt_root:
            parents.append(current)
            break
        # Stop if parent equals itself (invalid/null element behavior)
        if current == element:
            break
        parents.append(current)
        prev: coat.SceneElement = current
        current = current.parent()
        # Stop if parent() returns the same element (at root)
        if current == prev:
            break
        iterations += 1

    return parents


def collect_elements_with_parents(
    elements: list[coat.SceneElement],
) -> list[coat.SceneElement]:
    """
    Collect elements and all their parents (for visibility isolation).

    Args:
        elements: List of elements

    Returns:
        List of elements plus all their parent elements (deduplicated)
    """
    result: list[coat.SceneElement] = list(elements)
    for el in elements:
        for parent in collect_parent_chain(el):
            if not _element_in_list(parent, result):
                result.append(parent)
    return result


# =============================================================================
# ISOLATION STATE DETECTION
# =============================================================================

def is_visibility_isolated(
    keep_visible: list[coat.SceneElement],
    all_elements: list[coat.SceneElement],
) -> bool:
    """
    Check if scene is in "isolated" state for visibility.

    Isolated means: keep_visible elements (and their parents) are visible,
    everything else is hidden.

    Args:
        keep_visible: Elements that should be visible (the selection)
        all_elements: All elements in the scene

    Returns:
        True if scene is currently in isolated state
    """
    if not keep_visible or not all_elements:
        return False

    # Get elements + parents that should be visible
    should_be_visible: list[coat.SceneElement] = collect_elements_with_parents(
        keep_visible)

    for el in all_elements:
        is_in_keep: bool = _element_in_list(el, should_be_visible)
        if is_in_keep:
            # Should be visible
            if not el.visible():
                return False
        else:
            # Should be hidden
            if el.visible():
                return False

    return True


def is_ghost_isolated(
    keep_unghosted: list[coat.SceneElement],
    all_elements: list[coat.SceneElement],
) -> bool:
    """
    Check if scene is in "ghost isolated" state.

    Ghost isolated means: keep_unghosted elements are unghosted,
    everything else is ghosted. (No parent chain needed for ghost.)

    Args:
        keep_unghosted: Elements that should be unghosted (the selection)
        all_elements: All elements in the scene

    Returns:
        True if scene is currently in ghost isolated state
    """
    if not keep_unghosted or not all_elements:
        return False

    for el in all_elements:
        is_in_keep: bool = _element_in_list(el, keep_unghosted)
        if is_in_keep:
            # Should be unghosted
            if el.ghost():
                return False
        else:
            # Should be ghosted
            if not el.ghost():
                return False

    return True


# =============================================================================
# ELEMENT VISIBILITY OPERATIONS (Pure functions)
# =============================================================================

def set_visibility(elements: list[coat.SceneElement], visible: bool) -> int:
    """
    Set visibility state for a list of elements.

    Args:
        elements: List of elements to modify
        visible: True to show, False to hide

    Returns:
        Number of elements modified
    """
    count: int = 0
    for el in elements:
        el.setVisibility(visible)
        count += 1
    return count


def hide_elements(elements: list[coat.SceneElement]) -> int:
    """
    Hide a list of elements.

    Args:
        elements: List of elements to hide

    Returns:
        Number of elements hidden
    """
    return set_visibility(elements, False)


def show_elements(elements: list[coat.SceneElement]) -> int:
    """
    Show a list of elements.

    Args:
        elements: List of elements to show

    Returns:
        Number of elements shown
    """
    return set_visibility(elements, True)


def set_ghost(elements: list[coat.SceneElement], ghosted: bool) -> int:
    """
    Set ghost state for a list of elements.

    Args:
        elements: List of elements to modify
        ghosted: True to ghost, False to unghost

    Returns:
        Number of elements modified
    """
    count: int = 0
    for el in elements:
        el.setGhost(ghosted)
        count += 1
    return count


def ghost_elements(elements: list[coat.SceneElement]) -> int:
    """
    Ghost a list of elements.

    Args:
        elements: List of elements to ghost

    Returns:
        Number of elements ghosted
    """
    return set_ghost(elements, True)


def unghost_elements(elements: list[coat.SceneElement]) -> int:
    """
    Unghost a list of elements.

    Args:
        elements: List of elements to unghost

    Returns:
        Number of elements unghosted
    """
    return set_ghost(elements, False)


def invert_visibility_on_elements(elements: list[coat.SceneElement]) -> int:
    """
    Invert visibility on a list of elements.

    Args:
        elements: List of elements to invert

    Returns:
        Number of elements inverted
    """
    count: int = 0
    for el in elements:
        current: bool = el.visible()
        el.setVisibility(not current)
        count += 1
    return count


def invert_ghost_on_elements(elements: list[coat.SceneElement]) -> int:
    """
    Invert ghost state on a list of elements.

    Args:
        elements: List of elements to invert

    Returns:
        Number of elements inverted
    """
    count: int = 0
    for el in elements:
        current: bool = el.ghost()
        el.setGhost(not current)
        count += 1
    return count


# =============================================================================
# STATE CACHING
# =============================================================================

def cache_ghost_states(
    elements: list[coat.SceneElement]
) -> dict[int, bool]:
    """
    Cache the ghost state of all elements.

    Args:
        elements: List of elements to cache

    Returns:
        Dict mapping element id() to ghost state
    """
    return {id(el): el.ghost() for el in elements}


def restore_ghost_states(
    elements: list[coat.SceneElement],
    cache: dict[int, bool]
) -> int:
    """
    Restore ghost states from a cache.

    Args:
        elements: List of elements to restore
        cache: Dict from cache_ghost_states()

    Returns:
        Number of elements restored
    """
    count: int = 0
    for el in elements:
        el_id: int = id(el)
        if el_id in cache:
            el.setGhost(cache[el_id])
            count += 1
    return count


# =============================================================================
# FILTERED OPERATIONS
# =============================================================================


def hide_except(
    all_elements: list[coat.SceneElement],
    keep_visible: list[coat.SceneElement]
) -> int:
    """
    Hide all elements except those in the keep_visible list.

    Args:
        all_elements: All elements to consider
        keep_visible: Elements that should remain visible

    Returns:
        Number of elements hidden
    """
    to_hide: list[coat.SceneElement] = [
        el for el in all_elements if not _element_in_list(el, keep_visible)
    ]
    return hide_elements(to_hide)


def ghost_except(
    all_elements: list[coat.SceneElement],
    keep_unghosted: list[coat.SceneElement]
) -> int:
    """
    Ghost all elements except those in the keep_unghosted list.

    Args:
        all_elements: All elements to consider
        keep_unghosted: Elements that should remain unghosted

    Returns:
        Number of elements ghosted
    """
    to_ghost: list[coat.SceneElement] = [
        el for el in all_elements if not _element_in_list(el, keep_unghosted)
    ]
    return ghost_elements(to_ghost)


def isolate_visible_with_parents(
    all_elements: list[coat.SceneElement],
    selection: list[coat.SceneElement]
) -> int:
    """
    Isolate visibility: show selection + parents, hide everything else.

    Unlike hide_except, this considers parent chain so the path to the
    selected objects remains visible.

    Args:
        all_elements: All elements in the scene
        selection: Elements to keep visible (along with their parents)

    Returns:
        Number of elements hidden
    """
    # Get selection + all parent elements
    keep_visible: list[coat.SceneElement] = collect_elements_with_parents(
        selection)

    # Show the keep_visible elements first
    show_elements(keep_visible)

    # Hide everything else
    to_hide: list[coat.SceneElement] = [
        el for el in all_elements if not _element_in_list(el, keep_visible)
    ]
    return hide_elements(to_hide)


def toggle_visibility_isolation(
    all_elements: list[coat.SceneElement],
    selection: list[coat.SceneElement]
) -> tuple[bool, int]:
    """
    Toggle visibility isolation: if isolated, show all; else isolate.

    Args:
        all_elements: All elements in the scene
        selection: Elements to isolate (if not already isolated)

    Returns:
        Tuple of (is_now_isolated, count_affected)
    """
    if is_visibility_isolated(selection, all_elements):
        # Currently isolated - show all
        count: int = show_elements(all_elements)
        return (False, count)
    else:
        # Not isolated - isolate
        count = isolate_visible_with_parents(all_elements, selection)
        return (True, count)


def toggle_ghost_isolation(
    all_elements: list[coat.SceneElement],
    selection: list[coat.SceneElement]
) -> tuple[bool, int]:
    """
    Toggle ghost isolation: if ghost isolated, unghost all; else ghost isolate.

    Args:
        all_elements: All elements in the scene
        selection: Elements to keep unghosted (if not already isolated)

    Returns:
        Tuple of (is_now_isolated, count_affected)
    """
    if is_ghost_isolated(selection, all_elements):
        # Currently ghost isolated - unghost all
        count: int = unghost_elements(all_elements)
        return (False, count)
    else:
        # Not isolated - ghost isolate
        count = ghost_except(all_elements, selection)
        return (True, count)
