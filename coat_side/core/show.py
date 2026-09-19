"""
CoatMenu - entry points used by the menu items.

Both the menu item (``actions/CoatMenu_Show.py``) and any future hotkey path
funnel through here, so there is exactly one place that decides which list to
show and which trigger key to watch.
"""
from __future__ import annotations

from core import menu_data
from core.hotkeys import find_trigger_vk
from core.log import log
from ui import popup

# Id we register our menu item under (see install/install.py -> ExtraMenuItems)
MENU_HOTKEY_ID = "CoatMenu_Show"


def show_main_menu(script_path: str = "") -> None:
    """Show the CoatMenu overlay at the cursor."""
    try:
        items = menu_data.demo_items()
        if not items:
            log("show_main_menu: no items to show")
            return

        candidates = [MENU_HOTKEY_ID]
        if script_path:
            candidates.append("execute:" + script_path)
        vk = find_trigger_vk(candidates)
        log(f"show_main_menu: {len(items)} rows, trigger_vk={vk} ({menu_data.stats_line()})")

        popup.show_menu(items, trigger_vk=vk, title="CoatMenu")
    except Exception:
        log("show_main_menu failed", exc=True)


def hide_menu() -> None:
    popup.hide_menu()
