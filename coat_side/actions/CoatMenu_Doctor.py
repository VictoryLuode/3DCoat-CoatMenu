"""CoatMenu - write a status report the user can read or paste.

Menu item: Scripts > CoatMenu > CoatMenu_Doctor.
Output: ``<ext>/data/doctor.txt`` and the 3DCoat Python console.

The logging below is deliberately dependency-free: if importing our own package
fails, the reason has to still reach a file (we already had a sibling extension's
top-level package name shadow ours once).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _schedule_self_removal() -> None:
    """Let the next click re-run this module (3DCoat executes it by import)."""
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


def _log_raw(message: str) -> None:
    try:
        import coat  # type: ignore
        documents = str(coat.io.documents())
    except Exception:
        documents = os.path.join(os.path.expanduser("~"), "Documents")
    try:
        path = os.path.join(documents, "3DCoat", "CoatMenu.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"[doctor] {message}\n")
    except Exception:
        pass


def main() -> None:
    try:
        from coatmenu.core import doctor
        text = doctor.run()
        print(text)
    except Exception as exc:  # never break 3DCoat
        _log_raw(f"report failed: {exc!r}")


_schedule_self_removal()
main()
