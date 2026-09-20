"""
SculptObject_Proxy Operator

Toggle proxy mode (decimation/reduction cache) on sculpt objects.
Proxy mode provides faster viewport performance while preserving full resolution.

Proxy system has two steps:
1. Set proxy mode ($Decimate16X, $Reduce8X, etc.) - configures HOW objects will be proxied
2. Apply caching ($ToggleCachingVolume) - actually proxies/unproxies objects

Sync-Toggle (multi-object scopes):
When operating on multiple objects (TREE, ALL), the first object's current
proxy state is used as the reference.  All objects in the scope are synced
to the *opposite* state — so either all become cached or all become uncached.

Supports multiple proxy modes:
- Decimate: 16X, 8X, 4X, 2X (destructive decimation-based, more accurate)
- Reduce: 8X, 4X, 2X (non-destructive reduction, faster)

Uses scope resolution to determine which elements to operate on.
"""
import coat
from typing import Callable
from ported.utils.scene_api import SceneAPI, SelectionAPI
from ported.utils.scope_utils import Scope, resolve_scope
from ported.utils.Volume_proxy_utils import (
    set_proxy_mode, toggle_caching, ProxyMode, DEFAULT_PROXY_MODE
)
from ported.utils.coat_ui_utils import show_message, show_error


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _proxy_element(element: coat.SceneElement, proxy_mode: ProxyMode) -> bool:
    """
    Toggle proxy mode on a single element.

    Args:
        element: The SceneElement to proxy
        proxy_mode: The proxy mode to use

    Returns:
        True if element was processed, False if skipped
    """
    if not element.isSculptObject():
        return False

    # Select element for operation
    element.selectOne()

    # Set proxy mode first, then toggle caching
    set_proxy_mode(proxy_mode)
    toggle_caching()
    return True


def _proxy_element_if_needed(
    element: coat.SceneElement,
    proxy_mode: ProxyMode,
    *,
    toggle_when_cached: bool,
) -> bool:
    """Toggle proxy only if the element's current state doesn't match the target.

    Args:
        element: The SceneElement to potentially proxy.
        proxy_mode: The proxy mode to use.
        toggle_when_cached: If True, toggle only currently-cached objects.
            If False, toggle only currently-uncached objects.

    Returns:
        True if the element was toggled, False if skipped (already at target).
    """
    if not element.isSculptObject():
        return False

    element.selectOne()

    # Check current cached state
    currently_cached: bool = coat.is_proxy()

    # Only toggle if the current state needs to change
    if currently_cached == toggle_when_cached:
        set_proxy_mode(proxy_mode)
        toggle_caching()
        return True
    return False


# =============================================================================
# MAIN OPERATOR
# =============================================================================

def main(
    scope: Scope = Scope.CURRENT,
    proxy_mode: ProxyMode = DEFAULT_PROXY_MODE,
    preserve_selection: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Toggle proxy mode on objects.

    For single-object scopes (CURRENT), performs a simple flip-flop toggle.
    For multi-object scopes (TREE, ALL), uses sync-toggle: reads the first
    object's cached state, then pushes the *opposite* state to all objects
    in the scope.

    Args:
        scope: Which objects to operate on
        proxy_mode: Mode of proxy to toggle (DECIMATE_16X, REDUCE_8X, etc.)
        preserve_selection: Whether to restore selection after operation
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Number of objects toggled
    """
    # Save selection for restoration
    saved_selection: list[coat.SceneElement] = []
    if preserve_selection:
        saved_selection = SelectionAPI.save_selection()

    # Validation for scope check
    current: coat.SceneElement | None = SceneAPI.get_current_element()
    if scope in (Scope.CURRENT, Scope.TREE) and not current:
        show_error("No object selected", 2000)
        return 0

    # Resolve which elements to operate on
    elements: list[coat.SceneElement] = resolve_scope(scope)

    if not elements:
        show_error("No objects to process", 2000)
        return 0

    total: int = len(elements)

    # ── Sync-toggle for multi-object scopes ────────────────────────────
    if scope in (Scope.TREE, Scope.ALL):
        # Read the first element's proxy state as the reference
        first: coat.SceneElement = elements[0]
        first.selectOne()
        first_cached: bool = coat.is_proxy()

        # Target: push the opposite state to all elements
        # toggle_when_cached=True means "toggle cached ones → they become uncached"
        # toggle_when_cached=False means "toggle uncached ones → they become cached"
        toggle_target: bool = first_cached  # toggle the ones that match first's state

        count: int = 0
        for i, el in enumerate(elements):
            if progress_callback is not None:
                progress_callback(i, total, el.name())
            if _proxy_element_if_needed(el, proxy_mode, toggle_when_cached=toggle_target):
                count += 1

        # Restore selection
        if preserve_selection and saved_selection:
            SelectionAPI.restore_selection(saved_selection)

        action: str = "Uncached" if first_cached else "Cached"
        mode_name: str = proxy_mode.name.replace("_", " ").title()
        show_message(f"{action} {count} objects ({mode_name})", 2000)
        return count

    # ── Simple toggle for single-object scope ──────────────────────────
    count = 0
    for i, el in enumerate(elements):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if _proxy_element(el, proxy_mode):
            count += 1

    # Restore selection
    if preserve_selection and saved_selection:
        SelectionAPI.restore_selection(saved_selection)

    mode_name = proxy_mode.name.replace("_", " ").title()
    show_message(f"Toggled {mode_name} proxy on {count} objects", 2000)
    return count
