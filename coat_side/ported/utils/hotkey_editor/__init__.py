"""
Hotkey Editor Package

A Qt-based editor for 3DCoat hotkey bindings.

Usage:
    # From LKS panel (inside 3DCoat):
    from ported.utils.hotkey_editor import launch_hotkey_editor
    launch_hotkey_editor()
    
    # Standalone (for testing):
    from ported.utils.hotkey_editor import run_standalone
    run_standalone()
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Re-export main components for easy access
from .qt_imports import HAS_QT

if HAS_QT:
    from .main_window import HotkeyEditorWindow
    from .key_capture_dialog import KeyCaptureDialog
    from .conflict_resolution_dialog import ConflictResolutionDialog

from .styles import EDITOR_STYLESHEET
from .conflict_utils import count_conflicts, find_conflicts_with_global
from .hotkey_imports import discover_hotkeys_path

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


# =============================================================================
# LAUNCHER FUNCTIONS
# =============================================================================

def launch_hotkey_editor(
    path: Path | str | None = None,
    parent: "QWidget | None" = None,
) -> "HotkeyEditorWindow | None":
    """
    Launch the hotkey editor window.

    Can be called from inside 3DCoat (LKS panel) or standalone.

    Args:
        path: Path to hotkeys file (auto-detects if None)
        parent: Parent widget (for modal behavior)

    Returns:
        The editor window instance, or None if Qt not available
    """
    if not HAS_QT:
        print("ERROR: PySide6 not available")
        return None

    from PySide6.QtWidgets import QApplication

    # Ensure QApplication exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Convert path
    hotkeys_path: Path | None = None
    if path:
        hotkeys_path = Path(path)
    else:
        hotkeys_path = discover_hotkeys_path()

    # Create and show window
    window = HotkeyEditorWindow(hotkeys_path, parent)
    window.show()

    return window


def run_standalone(path: str | None = None) -> int:
    """
    Run the editor as a standalone application.

    Args:
        path: Path to hotkeys file (optional)

    Returns:
        Exit code
    """
    if not HAS_QT:
        print("ERROR: PySide6 is required. Install with: pip install PySide6")
        return 1

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Parse path argument
    hotkeys_path: Path | None = None
    if path:
        hotkeys_path = Path(path)
    elif len(sys.argv) > 1:
        hotkeys_path = Path(sys.argv[1])

    window = HotkeyEditorWindow(hotkeys_path)
    window.show()

    return app.exec()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Qt availability
    "HAS_QT",
    # Main classes (only available when HAS_QT)
    "HotkeyEditorWindow",
    "KeyCaptureDialog",
    "ConflictResolutionDialog",
    # Utilities
    "EDITOR_STYLESHEET",
    "count_conflicts",
    "find_conflicts_with_global",
    "discover_hotkeys_path",
    # Launchers
    "launch_hotkey_editor",
    "run_standalone",
]
