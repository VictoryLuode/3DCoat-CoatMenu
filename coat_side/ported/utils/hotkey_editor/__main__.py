"""
Hotkey Editor - CLI Entry Point

Run with:
    python -m ported.utils.hotkey_editor
    python -m ported.utils.hotkey_editor "C:/path/to/Options_Hotkeys.xml"
"""
from __future__ import annotations

import sys

# When running as __main__, we need to set up the import path
# to bypass the ported.utils/__init__.py which imports coat
if __name__ == "__main__":
    from pathlib import Path

    # Add LKS root to path so we can import ported.utils.hotkey_utils directly
    _lks_root = Path(__file__).parent.parent.parent
    if str(_lks_root) not in sys.path:
        sys.path.insert(0, str(_lks_root))

    # Now import and run
    from ported.utils.hotkey_editor import run_standalone

    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_standalone(path_arg))
