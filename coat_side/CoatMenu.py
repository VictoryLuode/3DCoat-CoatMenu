"""
CoatMenu - 3DCoat extension entry point.

3DCoat imports this module by name (the directory under
``UserPrefs/Scripts/cExtensions`` listed in ``startup.txt``) and keeps the
``cExtension`` instance alive. The per-frame hooks are what keep the Qt overlay
responsive: without ``processEvents()`` nothing on the overlay would ever run.

Rules learned from CoatLink / LKS (both live in this same 3DCoat install):

* 3DCoat imports scripts *by module name*, so ``__name__`` is never
  ``"__main__"`` - never guard the entry point with ``if __name__ == ...``.
* Per-frame code must have zero side effects on the scene. We only pump Qt
  events here; nothing touches the scene or the disk.
* Action scripts are cached in ``sys.modules``, so re-clicking the menu item
  would silently do nothing. The entry script queues itself for removal and we
  drop it here, one frame later (removing it during import raises KeyError).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import cPy.cCore  # noqa: E402

from core.log import log  # noqa: E402
from ui import popup  # noqa: E402

EXTENSION_NAME = "CoatMenu"


def _clear_queued_modules() -> None:
    """Drop action-script modules queued last frame so they can run again."""
    try:
        queued = getattr(sys, "_coatmenu_modules_to_clear", None)
        if not queued:
            return
        for name in list(queued):
            if name in sys.modules:
                del sys.modules[name]
        queued.clear()
    except Exception:
        log("module cache clear failed", exc=True)


class CoatMenuExtension(cPy.cCore.cExtension):
    """Keeps the Qt overlay alive and re-runnable."""

    _instance: "CoatMenuExtension | None" = None

    def __init__(self) -> None:
        cPy.cCore.cExtension.__init__(self)
        CoatMenuExtension._instance = self
        self._frames = 0
        log(f"{EXTENSION_NAME} extension created (source: {_HERE})")

    # -- lifecycle --------------------------------------------------------

    def onStartup(self) -> None:
        log(f"{EXTENSION_NAME} onStartup")

    def preprocess(self) -> None:
        """Once per frame, before tool processing: pump the Qt event loop."""
        self._frames += 1
        popup.tick()

    def postprocess(self) -> None:
        """Once per frame, after tool processing: housekeeping only."""
        _clear_queued_modules()

    def onChangeRoom(self) -> None:
        # The overlay is transient; a room switch must not leave it floating.
        popup.hide_menu()

    def onExit(self) -> None:
        log(f"{EXTENSION_NAME} exiting")
        try:
            popup.hide_menu()
        except Exception:
            pass

    @classmethod
    def instance(cls) -> "CoatMenuExtension | None":
        return cls._instance


# Registration is a side effect of instantiation (as in 3DCoat's own
# MouseTest tutorial) - unconditional, never guarded by __name__.
_extension = CoatMenuExtension()
