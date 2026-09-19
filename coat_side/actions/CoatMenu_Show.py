"""
CoatMenu - menu item entry point.

3DCoat runs this file when the user picks ``Scripts > CoatMenu > Show CoatMenu``
(or presses the key bound to that item). 3DCoat imports it by module name, so the
call at the bottom is unconditional.

Two hard-won details:

* the package imports happen *inside* main(), so a broken import is written to
  our own log file instead of only appearing in 3DCoat's ``python_error.txt``;
* the module queues itself for removal from ``sys.modules`` - the extension's
  ``postprocess`` drops it one frame later, otherwise the second click would hit
  the import cache and do nothing.
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
            fh.write(f"[entry:CoatMenu_Show] {message}\n")
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
        from coatmenu.core.show import apply_labels, show_main_menu
    except Exception:
        _log_raw("IMPORT FAILED\n" + traceback.format_exc())
        raise

    log("menu item: show (cExtension " +
        ("loaded)" if "CoatMenu" in sys.modules else "NOT loaded - restart 3DCoat or start it in Windows > Panels > Extensions)"))
    apply_labels()
    show_main_menu(script_path=os.path.abspath(__file__))


_schedule_self_removal()

try:
    main()
except Exception:
    _log_raw("RUN FAILED\n" + traceback.format_exc())
    raise
