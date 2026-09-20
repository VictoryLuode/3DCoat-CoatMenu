"""
Hotkey Editor - Hotkey Utils Import Helper

Handles importing hotkey_utils both from inside 3DCoat and standalone.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Detect if running inside 3DCoat's embedded Python
RUNNING_IN_3DCOAT: bool = False
try:
    import coat
    RUNNING_IN_3DCOAT = True
except ImportError:
    pass

# Import hotkey_utils with flexible path resolution
# Try relative import first (avoids triggering ported.utils/__init__.py which imports coat)
try:
    from ..hotkey_utils import (
        HotkeyEntry,
        HotkeysFile,
        HotkeyStats,
        VALID_ROOMS,
        parse_hotkeys_file,
        validate_all,
        remove_duplicates,
        remove_orphan_rooms,
        create_backup,
        list_backups,
        restore_backup,
        save_hotkeys_file,
        get_stats,
        discover_hotkeys_path,
    )
except (ImportError, ModuleNotFoundError):
    # Standalone mode: import from parent directory
    import importlib.util
    _hotkey_utils_path = Path(__file__).parent.parent / "hotkey_utils.py"
    _spec = importlib.util.spec_from_file_location(
        "hotkey_utils", _hotkey_utils_path)
    _hotkey_utils = importlib.util.module_from_spec(_spec)
    sys.modules["hotkey_utils"] = _hotkey_utils
    _spec.loader.exec_module(_hotkey_utils)

    HotkeyEntry = _hotkey_utils.HotkeyEntry
    HotkeysFile = _hotkey_utils.HotkeysFile
    HotkeyStats = _hotkey_utils.HotkeyStats
    VALID_ROOMS = _hotkey_utils.VALID_ROOMS
    parse_hotkeys_file = _hotkey_utils.parse_hotkeys_file
    validate_all = _hotkey_utils.validate_all
    remove_duplicates = _hotkey_utils.remove_duplicates
    remove_orphan_rooms = _hotkey_utils.remove_orphan_rooms
    create_backup = _hotkey_utils.create_backup
    list_backups = _hotkey_utils.list_backups
    restore_backup = _hotkey_utils.restore_backup
    save_hotkeys_file = _hotkey_utils.save_hotkeys_file
    get_stats = _hotkey_utils.get_stats
    discover_hotkeys_path = _hotkey_utils.discover_hotkeys_path
