"""
CoatMenu - menu item entry point.

3DCoat runs this file when the user picks ``Scripts > CoatMenu > Show CoatMenu``
(or presses the key bound to that item). 3DCoat imports it by module name, so
the call at the bottom is unconditional.

The module queues itself for removal from ``sys.modules`` - 3DCoat's
``CoatMenuExtension.postprocess`` drops it one frame later, otherwise the second
click would hit the import cache and do nothing.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.log import log  # noqa: E402
from core.show import show_main_menu  # noqa: E402


def main() -> None:
    log("menu item: show")
    show_main_menu(script_path=os.path.abspath(__file__))


main()

# Re-runnable on the next click.
if not hasattr(sys, "_coatmenu_modules_to_clear"):
    sys._coatmenu_modules_to_clear = set()
sys._coatmenu_modules_to_clear.add(__name__)
