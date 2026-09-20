"""
Hotkey Editor - Facade Module

This module provides backwards compatibility by re-exporting
from the modular ported.utils.hotkey_editor package.

For new code, import directly from the package:
    from ported.utils.hotkey_editor import launch_hotkey_editor, HotkeyEditorWindow

Usage:
    # From terminal (standalone, for testing outside 3DCoat):
    python -m ported.utils.hotkey_editor
    python -m ported.utils.hotkey_editor "C:/path/to/Options_Hotkeys.xml"
    
    # From LKS panel (inside 3DCoat):
    from ported.utils.hotkey_editor import launch_hotkey_editor
    launch_hotkey_editor()
"""
from __future__ import annotations

import sys

# =============================================================================
# RE-EXPORTS FROM MODULAR PACKAGE
# =============================================================================

from ported.utils.hotkey_editor import (
    HAS_QT,
    EDITOR_STYLESHEET,
    count_conflicts,
    find_conflicts_with_global,
    discover_hotkeys_path,
    launch_hotkey_editor,
    run_standalone,
)

if HAS_QT:
    from ported.utils.hotkey_editor import (
        HotkeyEditorWindow,
        KeyCaptureDialog,
        ConflictResolutionDialog,
    )

# Also re-export constants from styles for backwards compatibility
from ported.utils.hotkey_editor.styles import (
    COL_COMMAND,
    COL_KEY,
    COL_MODIFIERS,
    COL_ROOM,
    COL_STATUS,
    COL_USER_DEF,
    COL_STACKABLE,
    DEFAULT_GARBAGE_KEY,
    DEFAULT_GARBAGE_CTRL,
    DEFAULT_GARBAGE_ALT,
    DEFAULT_GARBAGE_SHIFT,
    COLOR_DUPLICATE,
    COLOR_CONFLICT,
    COLOR_ORPHAN,
    COLOR_NORMAL,
    COLOR_UNASSIGNED,
    COLOR_GARBAGE,
    ICON_DUPLICATE,
    ICON_CONFLICT,
    ICON_ORPHAN,
    ICON_GARBAGE,
    ICON_OK,
)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_standalone(path_arg))
