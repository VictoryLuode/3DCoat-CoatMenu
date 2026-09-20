"""
Action script discovery utilities.

Pure Python module for scanning and categorizing action scripts.
NO 3DCoat dependencies - can be tested outside of 3DCoat.

Usage:
    from ported.utils.action_discovery import discover_actions, ActionInfo
    actions = discover_actions(Path("actions"))
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# =============================================================================
# CONSTANTS
# =============================================================================

# Action scripts must match this pattern
ACTION_FILENAME_PATTERN: re.Pattern = re.compile(
    r'^([A-Z][a-zA-Z]+)_(.+)\.py$'
)

# Known context prefixes for categorization
KNOWN_CONTEXTS: set[str] = {
    "SculptObject",
    "Brush",
    "Scene",
    "Layer",
    "Autopo",
    "Export",
    "Shader",
    "Debug",
    "LKS",
}

# Scripts to exclude from auto-registration (panels, lifecycle scripts)
EXCLUDED_SCRIPTS: set[str] = {
    "LKS_Tools_Panel.py",
    "LKS_Register.py",
    "LKS_Unregister.py",
    "LKS_FullReload.py",
    "LKS_ExternalPanel_Launch.py",
    "LKS_ExternalPanel_Stop.py",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ActionInfo:
    """Information about a discovered action script."""
    filename: str
    path: Path
    context: str  # e.g., "SculptObject", "Brush", "Autopo"
    action_name: str  # e.g., "Decimate_Half_Selected"
    display_name: str  # e.g., "LKS: Decimate Half Selected"
    menu_id: str  # e.g., "LKS_Decimate_Half_Selected"

    @property
    def path_str(self) -> str:
        """Get path as forward-slash string for 3DCoat."""
        return str(self.path).replace("\\", "/")


@dataclass
class ActionCategory:
    """Group of actions by context."""
    context: str
    display_name: str
    actions: list[ActionInfo] = field(default_factory=list)


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def parse_action_filename(filename: str) -> tuple[str, str] | None:
    """
    Parse action filename into context and action name.

    Args:
        filename: Filename like "SculptObject_Decimate_Half_Selected.py"

    Returns:
        Tuple of (context, action_name) or None if doesn't match pattern
    """
    match: re.Match | None = ACTION_FILENAME_PATTERN.match(filename)
    if not match:
        return None

    context: str = match.group(1)
    rest: str = match.group(2)

    # Handle multi-word contexts like "SculptObject"
    # If context not in known list, try to find longest match
    if context not in KNOWN_CONTEXTS:
        # Check if it's a compound like "SculptObject" that got split
        for known in KNOWN_CONTEXTS:
            if filename.startswith(known + "_"):
                context = known
                rest = filename[len(known) + 1:-3]  # Remove .py
                break

    return (context, rest)


def generate_display_name(filename: str) -> str:
    """
    Generate human-readable display name from script filename.

    Args:
        filename: Full script filename like "SculptObject_Decimate_Half_Selected.py"

    Returns:
        Display name like "LKS: SculptObject_Decimate_Half_Selected.py"
    """
    return f"LKS: {filename}"


def generate_menu_id(context: str, action_name: str) -> str:
    """
    Generate unique menu ID for action registration.

    Args:
        context: e.g., "SculptObject"
        action_name: e.g., "Decimate_Half_Selected"

    Returns:
        Menu ID like "LKS_SculptObject_Decimate_Half_Selected"
    """
    return f"LKS_{context}_{action_name}"


# =============================================================================
# DISCOVERY FUNCTIONS
# =============================================================================

def discover_actions(actions_dir: Path) -> list[ActionInfo]:
    """
    Discover all action scripts in a directory.

    Args:
        actions_dir: Path to actions folder

    Returns:
        List of ActionInfo for all valid action scripts
    """
    actions: list[ActionInfo] = []

    if not actions_dir.exists():
        return actions

    for py_file in sorted(actions_dir.glob("*.py")):
        if py_file.name in EXCLUDED_SCRIPTS:
            continue

        if py_file.name.startswith("_"):
            continue

        parsed: tuple[str, str] | None = parse_action_filename(py_file.name)
        if parsed is None:
            continue

        context, action_name = parsed

        action = ActionInfo(
            filename=py_file.name,
            path=py_file,
            context=context,
            action_name=action_name,
            display_name=generate_display_name(py_file.name),
            menu_id=generate_menu_id(context, action_name),
        )
        actions.append(action)

    return actions


def group_actions_by_context(actions: list[ActionInfo]) -> list[ActionCategory]:
    """
    Group actions by their context for submenu organization.

    Args:
        actions: List of discovered actions

    Returns:
        List of ActionCategory with grouped actions
    """
    context_map: dict[str, ActionCategory] = {}

    for action in actions:
        if action.context not in context_map:
            # Generate display name for context
            display: str = action.context
            # Add spaces before capitals for readability
            display = re.sub(r'([a-z])([A-Z])', r'\1 \2', display)
            context_map[action.context] = ActionCategory(
                context=action.context,
                display_name=display,
                actions=[],
            )
        context_map[action.context].actions.append(action)

    # Sort by context name
    return sorted(context_map.values(), key=lambda c: c.context)


def iter_actions(actions_dir: Path) -> Iterator[ActionInfo]:
    """
    Iterate over discovered actions (generator version).

    Args:
        actions_dir: Path to actions folder

    Yields:
        ActionInfo for each valid action script
    """
    yield from discover_actions(actions_dir)


# =============================================================================
# CLI (for testing)
# =============================================================================

if __name__ == "__main__":
    import sys

    # Allow running from command line for testing
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])
    else:
        test_dir = Path(__file__).parent.parent / "actions"

    print(f"Scanning: {test_dir}")
    print("-" * 60)

    actions = discover_actions(test_dir)
    categories = group_actions_by_context(actions)

    for category in categories:
        print(f"\n[{category.display_name}] ({len(category.actions)} actions)")
        for action in category.actions:
            print(f"  - {action.display_name}")
            print(f"    ID: {action.menu_id}")
            print(f"    File: {action.filename}")

    print(f"\n{'-' * 60}")
    print(f"Total: {len(actions)} actions in {len(categories)} categories")
