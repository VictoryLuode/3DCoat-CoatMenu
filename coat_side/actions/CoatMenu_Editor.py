"""
CoatMenu - editor entry point (menu item / overlay row).

Opens the configuration panel. Like every 3DCoat action script this is imported
by module name, so the call at the bottom is unconditional and the module queues
itself for removal so the second click works too.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.log import log  # noqa: E402


def main() -> None:
    log("menu item: editor")
    from ui.editor import show_editor
    show_editor()


main()

# Re-runnable on the next click.
if not hasattr(sys, "_coatmenu_modules_to_clear"):
    sys._coatmenu_modules_to_clear = set()
sys._coatmenu_modules_to_clear.add(__name__)
