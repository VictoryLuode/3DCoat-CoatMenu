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
    """Absolute path of the log file (lazily resolved)."""
    global _LOG_PATH
    if _LOG_PATH is None:
        try:
            import coat  # type: ignore
            documents = coat.io.documents()
        except Exception:
            documents = os.path.join(os.path.expanduser("~"), "Documents")
        _LOG_PATH = os.path.join(str(documents), "3DCoat", _LOG_NAME)
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
