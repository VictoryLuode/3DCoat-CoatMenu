"""
3DCoat menu registration utilities.

Wraps coat.ui.insertInMenu and related functions with proper path resolution
and error handling. This module DEPENDS on the coat module.

Usage:
    from ported.utils.coat_menu_utils import register_action, register_actions_from_discovery
    from ported.utils.action_discovery import discover_actions
    
    actions = discover_actions(get_actions_dir())
    register_actions_from_discovery(actions)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import coat

if TYPE_CHECKING:
    from ported.utils.action_discovery import ActionInfo


# =============================================================================
# PATH RESOLUTION
# =============================================================================

def get_lks_root() -> Path:
    """
    Get the LKS cModule root directory.

    Uses __file__ to find the actual location, works even with junctions.

    Returns:
        Path to LKS cModule root
    """
    # This file is at LKS/ported.utils/coat_menu_utils.py
    # LKS root is parent of parent
    return Path(__file__).parent.parent.resolve()


def get_actions_dir() -> Path:
    """
    Get the actions directory.

    Returns:
        Path to LKS/actions folder
    """
    return get_lks_root() / "actions"


def resolve_script_path(script_path: Path) -> str:
    """
    Resolve a script path to the format 3DCoat expects.

    3DCoat expects forward slashes in paths.

    Args:
        script_path: Path object to script

    Returns:
        Forward-slash path string
    """
    return str(script_path.resolve()).replace("\\", "/")


# =============================================================================
# MENU REGISTRATION
# =============================================================================

# Target menu for LKS actions
LKS_MENU_NAME: str = "Scripts"


def register_action(
    menu_id: str,
    display_name: str,
    script_path: Path,
    menu_name: str = LKS_MENU_NAME,
    force: bool = False,
) -> bool:
    """
    Register a single action script in 3DCoat's menu.

    Args:
        menu_id: Unique identifier for the menu item
        display_name: Human-readable name shown in menu
        script_path: Path to the action script
        menu_name: Target menu (default: "Scripts")
        force: If True, delete stale XML and re-insert even if already registered

    Returns:
        True if newly registered, False if already existed (translation still updated)
    """
    # Always update translation (in case display name changed)
    coat.ui.addTranslation(menu_id, display_name)

    # If already registered and not forcing, just update translation
    if coat.ui.checkIfMenuItemInserted(menu_id) and not force:
        return False

    # If forcing re-registration, delete the stale XML file first
    if force:
        _delete_menu_xml(menu_id)

    # Get path in 3DCoat format
    path_str: str = resolve_script_path(script_path)

    # Insert into menu
    coat.ui.insertInMenu(menu_name, menu_id, path_str)

    return True


def _delete_menu_xml(menu_id: str) -> None:
    """
    Delete the stale ExtraMenuItems XML file for a menu_id.

    3DCoat persists menu registrations as XML files and loads them
    on restart. Deleting the XML forces a fresh insertInMenu with
    the current display name translation.
    """
    from pathlib import Path

    try:
        docs_path: str = coat.io.documents("")
        xml_path: Path = Path(docs_path) / "UserPrefs" / "Scripts" / "ExtraMenuItems" / f"{menu_id}.xml"
        if xml_path.exists():
            xml_path.unlink()
            print(f"[coat_menu_utils] Deleted stale XML: {xml_path.name}")
    except Exception as e:
        print(f"[coat_menu_utils] Failed to delete stale XML for {menu_id}: {e}")


def register_actions_from_discovery(
    actions: list[ActionInfo],
    menu_name: str = LKS_MENU_NAME,
) -> tuple[int, int]:
    """
    Register multiple actions from discovery results.

    Actions are sorted by display_name before registration so they
    appear alphabetically in the menu.

    Args:
        actions: List of ActionInfo from action_discovery
        menu_name: Target menu (default: "Scripts")

    Returns:
        Tuple of (registered_count, skipped_count)
    """
    registered: int = 0
    skipped: int = 0

    # Sort by display_name for alphabetical menu ordering
    sorted_actions: list[ActionInfo] = sorted(
        actions, key=lambda a: a.display_name
    )

    for action in sorted_actions:
        if register_action(
            menu_id=action.menu_id,
            display_name=action.display_name,
            script_path=action.path,
            menu_name=menu_name,
        ):
            registered += 1
        else:
            skipped += 1

    return (registered, skipped)


def unregister_all_lks_actions() -> int:
    """
    Unregister all LKS actions from the menu.

    Note: 3DCoat may not have a direct unregister API.
    This is a placeholder for cleanup during development.

    Returns:
        Count of actions that would be unregistered (informational)
    """
    # Import here to avoid circular dependency
    from ported.utils.action_discovery import discover_actions

    actions_dir: Path = get_actions_dir()
    actions = discover_actions(actions_dir)

    # Note: coat.ui doesn't have removeFromMenu
    # Items persist until 3DCoat restart
    # This function is informational only

    return len(actions)


# =============================================================================
# DEBUGGING
# =============================================================================

def log_registration_status() -> None:
    """
    Log the current registration status to 3DCoat's console.

    Useful for debugging menu registration issues.
    """
    from ported.utils.action_discovery import discover_actions, group_actions_by_context

    actions_dir: Path = get_actions_dir()
    actions = discover_actions(actions_dir)
    categories = group_actions_by_context(actions)

    lines: list[str] = [
        f"LKS Action Registration Status",
        f"Actions directory: {actions_dir}",
        f"Total actions: {len(actions)}",
        "",
    ]

    for category in categories:
        lines.append(f"[{category.display_name}]")
        for action in category.actions:
            is_registered: bool = coat.ui.checkIfMenuItemInserted(
                action.menu_id)
            status: str = "✓" if is_registered else "✗"
            lines.append(f"  {status} {action.display_name}")
        lines.append("")

    # Print to console
    for line in lines:
        print(line)


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_lks_menu() -> tuple[int, int]:
    """
    Discover and register all LKS action scripts.

    Call this from __onstartup.py to auto-register all actions.

    Returns:
        Tuple of (registered_count, skipped_count)
    """
    from ported.utils.action_discovery import discover_actions

    actions_dir: Path = get_actions_dir()
    actions = discover_actions(actions_dir)

    return register_actions_from_discovery(actions)
