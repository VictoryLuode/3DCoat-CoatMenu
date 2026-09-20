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

try:
    from coatmenu.core.log import log  # noqa: E402
except Exception:  # pragma: no cover - only when the package is broken
    import traceback

    def log(message: str, exc: bool = False) -> None:
        try:
            print(f"[CoatMenu] {message}")
            if exc:
                traceback.print_exc()
        except Exception:
            pass

EXTENSION_NAME = "CoatMenu"


def _popup():
    """Import the overlay lazily.

    Keeping Qt out of the module-level import graph means a Qt problem degrades
    to "no overlay" instead of blocking the extension from loading at all.
    """
    from coatmenu.ui import popup  # noqa: PLC0415
    return popup


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
        try:
            from coatmenu.core import menus
            menus.ensure_config()
            config = menus.get_config()
            # Installed from a .3dcpack there is no installer to run, and the
            # generated launchers / menu XML are not in the package (they depend on
            # the user's config, and the paths inside them are absolute). 3DCoat
            # reads both at startup, so bring them up to date here. Nothing is
            # rewritten when it is already current.
            menus.sync_config(config, register=False)
            menus.register_menu_items(config)
        except Exception:
            log("onStartup list registration failed", exc=True)
        log(f"{EXTENSION_NAME} onStartup")

    def onBuildMainMenu(self) -> None:
        """Menu labels come from the translation table - make sure ours is in it.

        Also the one moment 3DCoat lets us add menu entries through its own API,
        which is how a menu gets the key set in the editor (see
        ``menus.register_menu_api``).
        """
        try:
            from coatmenu.core.show import apply_labels
            apply_labels()
        except Exception:
            pass
        try:
            from coatmenu.core import menus
            menus.register_menu_api()
        except Exception:
            log("menu api registration failed", exc=True)

    def preprocess(self) -> None:
        """Once per frame, before tool processing: pump the Qt event loop."""
        self._frames += 1
        try:
            _popup().tick()
        except Exception:
            # Never spam: report at most once every ~300 frames.
            if self._frames % 300 == 0:
                log("qt pump failed", exc=True)

    def postprocess(self) -> None:
        """Once per frame, after tool processing: housekeeping only."""
        _clear_queued_modules()

    def onChangeRoom(self) -> None:
        # The overlay is transient; a room switch must not leave it floating.
        try:
            _popup().hide_menu()
        except Exception:
            pass

    def onExit(self) -> None:
        log(f"{EXTENSION_NAME} exiting")
        try:
            _popup().hide_menu()
        except Exception:
            pass

    @classmethod
    def instance(cls) -> "CoatMenuExtension | None":
        return cls._instance


# Registration is a side effect of instantiation (as in 3DCoat's own
# MouseTest tutorial) - unconditional, never guarded by __name__.
_extension = CoatMenuExtension()
