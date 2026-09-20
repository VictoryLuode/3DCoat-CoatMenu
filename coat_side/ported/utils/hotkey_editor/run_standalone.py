#!/usr/bin/env python
"""
Standalone test runner for the hotkey editor.

Run from the LKS root directory:
    python ported.utils/hotkey_editor/run_standalone.py
    python ported.utils/hotkey_editor/run_standalone.py "C:/path/to/Options_Hotkeys.xml"
"""
from __future__ import annotations
import types

import sys
from pathlib import Path

# Setup import paths to avoid loading ported.utils/__init__.py
_SCRIPT_DIR = Path(__file__).parent
_UTILS_DIR = _SCRIPT_DIR.parent
_LKS_ROOT = _UTILS_DIR.parent

# Monkey-patch: create a fake ported.utils module so that importing
# ported.utils.hotkey_editor / ported.utils.hotkey_utils / ported.utils.keycode_map
# does NOT trigger ported.utils/__init__.py (which requires coat).
fake_utils = types.ModuleType("ported.utils")
fake_utils.__path__ = [str(_UTILS_DIR)]
sys.modules["ported.utils"] = fake_utils

# Ensure LKS root is on sys.path so that hotkey_editor's relative
# imports within ported.utils/ can resolve.
sys.path.insert(0, str(_LKS_ROOT))


def main() -> int:
    """Run the hotkey editor standalone."""
    # CRITICAL: QApplication MUST be created before importing any
    # hotkey_editor module.  qt_imports.py imports QPixmap from
    # PySide6.QtGui, and QPixmap requires an existing QApplication
    # on this platform — without it the process crashes with
    # STATUS_STACK_BUFFER_OVERRUN (0xC0000409).
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    from ported.utils.hotkey_editor.qt_imports import HAS_QT

    if not HAS_QT:
        print("ERROR: PySide6 is required. Install with: pip install PySide6")
        return 1

    from ported.utils.hotkey_editor.main_window import HotkeyEditorWindow
    from ported.utils.hotkey_editor.hotkey_imports import discover_hotkeys_path

    # Parse path argument
    hotkeys_path: Path | None = None
    if len(sys.argv) > 1:
        hotkeys_path = Path(sys.argv[1])
    else:
        hotkeys_path = discover_hotkeys_path()

    if hotkeys_path:
        print(f"Loading: {hotkeys_path}")
    else:
        print("No hotkeys file specified or found. Opening empty editor.")

    window = HotkeyEditorWindow(hotkeys_path)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
