"""
SceneElement Boolean Utilities - Live boolean operations on SceneElements.

Creates child boolean volumes for sculpt objects. Requires parent to be in voxel mode.

Pattern:
    from ported.utils.SceneElement_boolean_utils import create_boolean_child, BooleanMode
    
    create_boolean_child(parent_element, BooleanMode.SUBTRACT)
"""
import coat
from enum import IntEnum
from typing import Callable

from ported.utils.coat_ui_utils import wait_frames, show_message, show_error, CMD_DIALOG_OK
from ported.utils.Volume_mode_utils import ensure_voxel_mode


# =============================================================================
# BOOLEAN MAGIC UI STRINGS
# =============================================================================

CMD_EXTRUDE_VO: str = "$ExtrudeVO"
SETTING_EXTRUSION: str = "$ExtrudeParams::Extrusion"


# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_EXTRUSION: float = 1.0
BOOLEAN_WAIT_FRAMES: int = 4


# =============================================================================
# BOOLEAN MODE ENUM
# =============================================================================

class BooleanMode(IntEnum):
    """Live boolean operation modes (matches coat Volume.assignLiveBooleans)."""
    NONE = 0       # Stop live booleans
    SUBTRACT = 1   # Subtract from parent
    INTERSECT = 2  # Intersect with parent
    UNION = 3      # Union with parent


# Mode to suffix mapping (canonical case)
BOOLEAN_SUFFIXES: dict[BooleanMode, str] = {
    BooleanMode.NONE: "",
    BooleanMode.SUBTRACT: "_Subtract",
    BooleanMode.INTERSECT: "_Intersect",
    BooleanMode.UNION: "_Union",
}

# All recognised boolean suffixes for stripping (case-insensitive match).
# Lowercase form is what we compare against.
_BOOLEAN_SUFFIX_LOWER: tuple[str, ...] = (
    "_subtract",
    "_intersect",
    "_union",
)


# =============================================================================
# SUFFIX MANAGEMENT
# =============================================================================

def strip_boolean_suffix(name: str) -> str:
    """
    Remove a single trailing boolean suffix from `name`, if present.

    Matches `_Subtract`, `_Intersect`, `_Union` case-insensitively.
    Only ONE suffix is stripped to prevent over-trimming user names like
    "MyShape_Union_Backup".

    Args:
        name: Element name to clean

    Returns:
        Name with trailing boolean suffix removed (or unchanged if none).
    """
    lower: str = name.lower()
    for suffix in _BOOLEAN_SUFFIX_LOWER:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return name


def apply_boolean_suffix(name: str, mode: BooleanMode) -> str:
    """
    Return `name` with the suffix appropriate to `mode`.

    Strips any existing boolean suffix first so we never end up with
    chained suffixes (e.g. `_Union_Intersect`). For `BooleanMode.NONE`,
    the result has no suffix at all.

    Args:
        name: Current element name
        mode: Target boolean mode

    Returns:
        Cleaned name with the canonical suffix appended (or none for NONE).
    """
    base: str = strip_boolean_suffix(name)
    suffix: str = BOOLEAN_SUFFIXES.get(mode, "")
    return f"{base}{suffix}"


def rename_with_boolean_suffix(
    element: coat.SceneElement,
    mode: BooleanMode,
) -> str:
    """
    Rename `element` so it carries exactly the suffix for `mode`.

    Args:
        element: SceneElement to rename
        mode: Target boolean mode

    Returns:
        The new element name.
    """
    new_name: str = apply_boolean_suffix(element.name(), mode)
    if new_name != element.name():
        element.rename(new_name)
    return new_name


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def create_boolean_child(
    parent: coat.SceneElement,
    mode: BooleanMode,
    apply_extrusion: bool = False,
    extrusion_amount: float = DEFAULT_EXTRUSION,
    clear_child: bool = True,
) -> coat.SceneElement | None:
    """
    Create a child element with live boolean applied.

    Duplicates the parent, parents the clone under it, and sets up live boolean.
    Parent must be in voxel mode for booleans to work.

    CRITICAL: For INTERSECT, extrusion MUST be applied BEFORE setting boolean mode
    to prevent 3DCoat crash. For SUBTRACT/UNION, we clear child content first.

    Args:
        parent: The parent SceneElement to create boolean child for
        mode: The boolean mode (SUBTRACT, INTERSECT, UNION)
        apply_extrusion: Whether to apply voxel extrusion (required for INTERSECT)
        extrusion_amount: Amount of extrusion if apply_extrusion is True
        clear_child: Whether to clear the child's geometry (for SUBTRACT/UNION)

    Returns:
        The created boolean child element, or None if failed
    """
    if not parent:
        show_message("No parent element provided", 3000)
        return None

    # Ensure parent is a sculpt object
    if not parent.isSculptObject():
        show_error("Parent must be a sculpt object", 3000)
        return None

    # Ensure parent is in voxel mode (required for live booleans)
    parent_vol: coat.Volume = parent.Volume()
    if parent_vol.isSurface():
        show_message("Converting parent to voxel mode...", 2000)
        ensure_voxel_mode(parent_vol)
        wait_frames(BOOLEAN_WAIT_FRAMES)

    # Duplicate parent (child inherits voxel mode from parent)
    # NOTE: parent.duplicate() clones the entire subtree, so the new `child`
    # may itself have descendants we don't want. Strip them by removing each
    # direct child from highest index down (removeSubtree on `child` itself
    # would delete `child`; removeSubtreeItem(i) removes the i-th child).
    child: coat.SceneElement = parent.duplicate()
    wait_frames(BOOLEAN_WAIT_FRAMES)

    descendant_count: int = child.childCount()
    if descendant_count > 0:
        for i in range(descendant_count - 1, -1, -1):
            child.removeSubtreeItem(i)
        wait_frames(BOOLEAN_WAIT_FRAMES)

    # Rename with suffix (strip any existing boolean suffix from parent's
    # name first so cloning a `Foo_Union` parent yields `Foo_Subtract`,
    # never `Foo_Union_Subtract`).
    child.rename(apply_boolean_suffix(parent.name(), mode))
    wait_frames(BOOLEAN_WAIT_FRAMES)

    # Parent under original (no selectOne — caller manages selection)
    child.changeParent(parent)
    wait_frames(BOOLEAN_WAIT_FRAMES)

    # For INTERSECT: extrusion MUST be applied BEFORE setting boolean mode
    # For SUBTRACT/UNION: clear content first
    if apply_extrusion:
        # Apply extrusion first (CRITICAL: before assignLiveBooleans to avoid crash)
        _apply_voxel_extrusion(extrusion_amount)
        wait_frames(BOOLEAN_WAIT_FRAMES)
    elif clear_child:
        # Clear geometry for subtract/union (user will sculpt new geometry)
        child.clear()
        wait_frames(BOOLEAN_WAIT_FRAMES)

    # Now set boolean mode (after extrusion/clear to avoid crash)
    vol: coat.Volume = child.Volume()
    vol.assignLiveBooleans(int(mode))

    return child


def _apply_voxel_extrusion(amount: float = DEFAULT_EXTRUSION) -> None:
    """
    Apply voxel extrusion to current selection.

    Args:
        amount: Extrusion amount
    """
    def extrude_configurator() -> None:
        wait_frames(BOOLEAN_WAIT_FRAMES)
        coat.ui.setSliderValue(SETTING_EXTRUSION, amount)
        wait_frames(BOOLEAN_WAIT_FRAMES)
        coat.ui.cmd(CMD_DIALOG_OK)

    coat.ui.cmd(CMD_EXTRUDE_VO, extrude_configurator)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_subtract_child(parent: coat.SceneElement) -> coat.SceneElement | None:
    """Create a subtract boolean child (empty, ready for sculpting)."""
    return create_boolean_child(parent, BooleanMode.SUBTRACT, clear_child=True)


def create_intersect_child(
    parent: coat.SceneElement,
    extrusion: float = DEFAULT_EXTRUSION
) -> coat.SceneElement | None:
    """Create an intersect boolean child with extrusion applied."""
    return create_boolean_child(
        parent,
        BooleanMode.INTERSECT,
        apply_extrusion=True,
        extrusion_amount=extrusion
    )


def create_union_child(parent: coat.SceneElement) -> coat.SceneElement | None:
    """Create a union boolean child (empty, ready for sculpting)."""
    return create_boolean_child(parent, BooleanMode.UNION, clear_child=True)


def stop_boolean(element: coat.SceneElement) -> None:
    """Remove live boolean from an element."""
    vol: coat.Volume = element.Volume()
    vol.assignLiveBooleans(int(BooleanMode.NONE))


# =============================================================================
# LIVE BOOLEAN MODE SETTERS (operate on existing elements — no cloning)
# =============================================================================

def set_live_boolean_mode(
    element: coat.SceneElement,
    mode: BooleanMode,
) -> bool:
    """
    Set the live boolean mode on an existing element (no cloning).

    Behaviour:
        - For mode != NONE: ensures BOTH the element AND its parent sculpt
          object are in voxel mode (live booleans only work on voxels).
        - Renames the element with the canonical suffix for `mode`,
          stripping any pre-existing boolean suffix so we never chain
          (e.g. `Foo_Union_Subtract`).
        - For mode == NONE the boolean suffix is removed from the name.

    Args:
        element: The SceneElement to set the boolean mode on
        mode: The desired BooleanMode (NONE / SUBTRACT / INTERSECT / UNION)

    Returns:
        True if the mode was set, False if element is not a sculpt object
    """
    if not element or not element.isSculptObject():
        return False

    # For active boolean modes, both element and parent must be voxel.
    if mode != BooleanMode.NONE:
        vol: coat.Volume = element.Volume()
        if vol.isSurface():
            ensure_voxel_mode(vol)
            wait_frames(BOOLEAN_WAIT_FRAMES)

        parent: coat.SceneElement | None = element.parent()
        if parent is not None and parent.isSculptObject():
            parent_vol: coat.Volume = parent.Volume()
            if parent_vol.isSurface():
                ensure_voxel_mode(parent_vol)
                wait_frames(BOOLEAN_WAIT_FRAMES)

    vol = element.Volume()
    vol.assignLiveBooleans(int(mode))

    # Update name suffix to match new mode.
    rename_with_boolean_suffix(element, mode)
    return True


def set_live_boolean_mode_on_elements(
    elements: list[coat.SceneElement],
    mode: BooleanMode,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> int:
    """
    Set live boolean mode on a list of elements.

    Args:
        elements: List of SceneElements to update
        mode: The desired BooleanMode
        progress_callback: Called per-item as (index, total, name) for progress logging

    Returns:
        Count of elements that were successfully updated
    """
    total: int = len(elements)
    count: int = 0
    for i, el in enumerate(elements):
        if progress_callback is not None:
            progress_callback(i, total, el.name())
        if set_live_boolean_mode(el, mode):
            count += 1
    return count


# =============================================================================
# COLLAPSE / APPLY BOOLEAN TREE
# =============================================================================

def collapse_boolean_tree(element: coat.SceneElement) -> bool:
    """
    Collapse the live-boolean subtree under `element` (apply booleans).

    Wraps `Volume.collapseBollTree()` (note 3DCoat's typo). The element's
    boolean suffix is also stripped, since after collapsing the result is
    a plain object (no longer a boolean child).

    Args:
        element: The SceneElement whose boolean tree should be applied

    Returns:
        True on success, False if element is not a sculpt object.
    """
    if not element or not element.isSculptObject():
        return False
    vol: coat.Volume = element.Volume()
    vol.collapseBollTree()
    wait_frames(BOOLEAN_WAIT_FRAMES)

    # After collapse the element is a plain object - strip any boolean suffix.
    cleaned: str = strip_boolean_suffix(element.name())
    if cleaned != element.name():
        element.rename(cleaned)
    return True


def collapse_boolean_tree_keep_original(
    element: coat.SceneElement,
) -> coat.SceneElement | None:
    """
    Apply booleans on a duplicate, hide the original.

    Duplicates `element` (along with its boolean subtree), collapses the
    duplicate's boolean tree, and hides the original so the user retains
    a non-destructive copy.

    Args:
        element: The element whose boolean tree should be applied

    Returns:
        The duplicated/collapsed element, or None on failure.
    """
    if not element or not element.isSculptObject():
        return None

    duplicate: coat.SceneElement = element.duplicate()
    wait_frames(BOOLEAN_WAIT_FRAMES)

    # Hide the original AFTER duplicating so we keep an editable backup.
    element.setVisibility(False)

    # Name the duplicate as "<base>_Applied" so it's distinguishable.
    base: str = strip_boolean_suffix(element.name())
    duplicate.rename(f"{base}_Applied")
    wait_frames(BOOLEAN_WAIT_FRAMES)

    duplicate.selectOne()
    wait_frames(BOOLEAN_WAIT_FRAMES)

    dup_vol: coat.Volume = duplicate.Volume()
    dup_vol.collapseBollTree()
    wait_frames(BOOLEAN_WAIT_FRAMES)

    return duplicate
