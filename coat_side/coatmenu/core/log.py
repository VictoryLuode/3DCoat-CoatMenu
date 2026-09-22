"""
CoatMenu - logging.

Writes to ``<Documents>/3DCoat/CoatMenu.log`` (shared breadcrumb file, same
idea as CoatBridge.log) and mirrors to the 3DCoat Python console.

Never raises: logging must not be able to break the host application.
"""
from __future__ import annotations

import os
import time

_LOG_NAME = "CoatMenu.log"
_LOG_PATH: str | None = None


def log_path() -> str:
    """Absolute path of the log file (lazily resolved).

    ``COATMENU_LOG_PATH`` overrides it (tests, and hand debugging without
    touching the real log).
    """
    global _LOG_PATH
    if _LOG_PATH is None:
        override = os.environ.get("COATMENU_LOG_PATH")
        if override:
            _LOG_PATH = override
            return _LOG_PATH
        try:
            from coatmenu.core import paths
            data_root = paths.data_root()
        except Exception:
            data_root = os.path.join(os.path.expanduser("~"), "Documents", "3DCoat")
        _LOG_PATH = os.path.join(str(data_root), _LOG_NAME)
    return _LOG_PATH


def log(message: str, exc: bool = False) -> None:
    """Append one line to the log file and echo it to the console."""
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    try:
        print(f"[CoatMenu] {message}")
    except Exception:
        pass
    try:
        path = log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    if exc:
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass
