"""
Volume Proxy Utilities - Proxy mode operations on Volumes.

Low-level primitives with RAW ARGUMENTS ONLY (no dataclasses).
Proxy mode is 3DCoat's decimation cache for faster viewport performance.

Proxy system has two steps:
1. Set proxy mode ($Decimate16X, $Reduce8X, etc.) - configures HOW objects will be proxied
2. Apply caching ($ToggleCachingVolume, $CacheVisible, etc.) - actually proxies/unproxies objects

Supports multiple proxy levels:
- Decimate: 16X, 8X, 4X, 2X (destructive decimation-based, more accurate)
- Reduce: 8X, 4X, 2X (non-destructive reduction, faster)
"""
import coat
from enum import Enum

from ported.utils.coat_ui_utils import wait_frames

# =============================================================================
# MAGIC UI STRINGS (NOT in coat.pyi - discovered experimentally)
# =============================================================================

# Proxy MODE commands - set HOW objects will be proxied (decimate algorithm)
CMD_DECIMATE_16X: str = "$Decimate16X"
CMD_DECIMATE_8X: str = "$Decimate8X"
CMD_DECIMATE_4X: str = "$Decimate4X"
CMD_DECIMATE_2X: str = "$Decimate2X"

# Proxy MODE commands - set HOW objects will be proxied (reduce/resample algorithm)
CMD_REDUCE_8X: str = "$Reduce8X"
CMD_REDUCE_4X: str = "$Reduce4X"
CMD_REDUCE_2X: str = "$Reduce2X"

# Proxy ACTION commands - actually apply/remove caching on objects
CMD_TOGGLE_CACHING: str = "$ToggleCachingVolume"
CMD_CACHE_VISIBLE: str = "$CacheVisible"
CMD_UNCACHE_VISIBLE: str = "$UnCacheVisible"
CMD_CLEAR_ALL_CACHES: str = "$ClearAllCache"

# =============================================================================
# ENUMS
# =============================================================================


class ProxyMode(Enum):
    """Available proxy modes in 3DCoat (determines how objects are decimated)."""
    DECIMATE_16X = CMD_DECIMATE_16X
    DECIMATE_8X = CMD_DECIMATE_8X
    DECIMATE_4X = CMD_DECIMATE_4X
    DECIMATE_2X = CMD_DECIMATE_2X
    REDUCE_8X = CMD_REDUCE_8X
    REDUCE_4X = CMD_REDUCE_4X
    REDUCE_2X = CMD_REDUCE_2X


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_PROXY_MODE: ProxyMode = ProxyMode.DECIMATE_16X
MESH_OP_WAIT_FRAMES: int = 2


# =============================================================================
# MODE SETTING FUNCTIONS (set how proxy will work)
# =============================================================================

def set_proxy_mode(mode: ProxyMode = DEFAULT_PROXY_MODE) -> None:
    """
    Set the proxy mode (how objects will be decimated when cached).

    Args:
        mode: The proxy mode to set (default: DECIMATE_16X)

    This does NOT actually proxy any objects - it just sets the mode.
    Call toggle_caching() or cache_visible() to actually apply caching.
    """
    coat.ui.cmd(mode.value)
    wait_frames(MESH_OP_WAIT_FRAMES)


# =============================================================================
# CACHING ACTION FUNCTIONS (apply/remove proxy on objects)
# =============================================================================

def toggle_caching() -> None:
    """Toggle proxy/cache on current Volume."""
    coat.ui.cmd(CMD_TOGGLE_CACHING)
    wait_frames(MESH_OP_WAIT_FRAMES)


def cache_visible() -> None:
    """Cache all visible objects."""
    coat.ui.cmd(CMD_CACHE_VISIBLE)
    wait_frames(MESH_OP_WAIT_FRAMES)


def uncache_visible() -> None:
    """Uncache all visible objects."""
    coat.ui.cmd(CMD_UNCACHE_VISIBLE)
    wait_frames(MESH_OP_WAIT_FRAMES)


def clear_all_caches() -> None:
    """Clear all cached objects (restore full resolution)."""
    coat.ui.cmd(CMD_CLEAR_ALL_CACHES)
    wait_frames(MESH_OP_WAIT_FRAMES)


# =============================================================================
# HIGH-LEVEL CONVENIENCE FUNCTIONS (set mode + apply)
# =============================================================================

def proxy_current(mode: ProxyMode = DEFAULT_PROXY_MODE) -> None:
    """
    Set proxy mode and toggle caching on current Volume.

    Args:
        mode: The proxy mode to use (default: DECIMATE_16X)
    """
    set_proxy_mode(mode)
    toggle_caching()


def proxy_visible(mode: ProxyMode = DEFAULT_PROXY_MODE) -> None:
    """
    Set proxy mode and cache all visible objects.

    Args:
        mode: The proxy mode to use (default: DECIMATE_16X)
    """
    set_proxy_mode(mode)
    cache_visible()


# =============================================================================
# SHORTCUT FUNCTIONS
# =============================================================================

def toggle_decimate_16x() -> None:
    """Set 16X decimate mode and toggle caching on current Volume."""
    proxy_current(ProxyMode.DECIMATE_16X)


def toggle_decimate_8x() -> None:
    """Set 8X decimate mode and toggle caching on current Volume."""
    proxy_current(ProxyMode.DECIMATE_8X)


def toggle_decimate_4x() -> None:
    """Set 4X decimate mode and toggle caching on current Volume."""
    proxy_current(ProxyMode.DECIMATE_4X)


def toggle_reduce_8x() -> None:
    """Set 8X reduce mode and toggle caching on current Volume."""
    proxy_current(ProxyMode.REDUCE_8X)
