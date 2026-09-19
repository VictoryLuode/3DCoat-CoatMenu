"""
CoatMenu - editor entry point (menu item / overlay row).

Opens the configuration panel. Same rules as the show entry: imported by module
name, unconditional call, deferred module-cache removal, and the package imports
inside main() so a failure lands in our own log file.
"""
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _log_raw(message: str) -> None:
    """Append to CoatMenu.log without importing our package (it may be broken)."""
    try:
        path = os.environ.get("COATMENU_LOG_PATH") or os.path.join(
            os.path.expanduser("~"), "Documents", "3DCoat", "CoatMenu.log"
        )
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"[entry:CoatMenu_Editor] {message}\n")
    except Exception:
        pass
    try:
        print(f"[CoatMenu] {message}")
    except Exception:
        pass


def _schedule_self_removal() -> None:
    """Arrange for the *next* click of this menu item to run again.

    3DCoat executes a menu script as ``exec("import <module name>")``, so a second
    click would hit the import cache and silently do nothing. Two independent
    cleanup paths, because the extension's per-frame hook may not be running:

    * the extension's postprocess queue (when the cExtension is loaded), and
    * a Qt single-shot, since 3DCoat's own ``QT`` cExtension keeps an event loop
      pumping either way.
    """
    try:
        queue = getattr(sys, "_coatmenu_modules_to_clear", None)
        if queue is None:
            queue = set()
            sys._coatmenu_modules_to_clear = queue
        queue.add(__name__)
    except Exception:
        pass
    try:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda name=__name__: sys.modules.pop(name, None))
    except Exception:
        pass


def main() -> None:
    try:
        from coatmenu.core.log import log
        from coatmenu.ui.editor import show_editor
    except Exception:
        _log_raw("IMPORT FAILED\n" + traceback.format_exc())
        raise

    log("menu item: editor")
    show_editor()


_schedule_self_removal()

try:
    main()
except Exception:
    _log_raw("RUN FAILED\n" + traceback.format_exc())
    raise
