"""
CoatMenu - entry points used by the menu items and the editor's preview.

Two shapes:

* ``show_main_menu`` - the index: one row per configured list, each row a
  submenu, so hovering it opens that list.
* ``show_list`` - one list, flat - what each generated launcher script calls.
"""
from __future__ import annotations

import os

from coatmenu.core import lists, paths
from coatmenu.core.config import MenuConfig
from coatmenu.core.hotkeys import find_trigger_vk
from coatmenu.core.lists_registry import MAIN_MENU_ID, MAIN_MENU_LABEL, menu_entries
from coatmenu.core.log import log
from coatmenu.core.menu_model import MenuItem, separator, submenu
from coatmenu.ui import popup

# Main entry id/label (kept as module constants for callers and tests).
MENU_HOTKEY_ID = MAIN_MENU_ID
MENU_LABEL = MAIN_MENU_LABEL


def apply_labels() -> None:
    """Give our menu items readable labels.

    3DCoat shows the raw id unless the id has a translation entry, so this is
    (re)applied at startup, when the main menu is built and on every invocation.
    """
    try:
        import coat  # type: ignore
    except Exception:
        return
    config = lists.get_config()
    for menu_id, label, _script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir()
    ):
        try:
            coat.ui.addTranslation(menu_id, label)
        except Exception as exc:
            log(f"addTranslation({menu_id}) failed: {exc}")


def _config() -> MenuConfig:
    # ensure_config also regenerates launchers + menu XML if the config changed
    # on disk (e.g. the file was copied in by hand).
    return lists.ensure_config()


def show_main_menu(script_path: str = "") -> None:
    """Show the list index at the cursor."""
    try:
        config = _config()
        rows: list[MenuItem] = [submenu(lst.name, lst.items) for lst in config.lists]
        if not rows:
            log("show_main_menu: no lists configured")
            return
        # The editor is one row away, so the flow is: open menu, tweak, save.
        rows.append(separator())
        rows.append(
            MenuItem(
                label="Edit lists\u2026",
                kind="script",
                path=os.path.join(paths.extension_root(), "actions", "CoatMenu_Editor.py"),
            )
        )
        candidates = [MAIN_MENU_ID]
        if script_path:
            candidates.append("execute:" + script_path)
        vk = find_trigger_vk(candidates)
        log(f"show_main_menu: {len(rows)} list(s), trigger_vk={vk}")
        popup.show_menu(rows, trigger_vk=vk, title="CoatMenu")
    except Exception:
        log("show_main_menu failed", exc=True)


def show_list(key: str, script_path: str = "") -> None:
    """Show one configured list flat (called by its generated launcher)."""
    try:
        config = _config()
        target = config.find(key)
        if target is None:
            log(f"show_list: unknown list {key!r} - showing the index instead")
            show_main_menu(script_path)
            return
        candidates = [target.hotkey_id]
        if script_path:
            candidates.append("execute:" + script_path)
        vk = find_trigger_vk(candidates)
        log(f"show_list: {target.name} ({len(target.items)} rows), trigger_vk={vk}")
        popup.show_menu(target.items, trigger_vk=vk, title=target.name)
    except Exception:
        log("show_list failed", exc=True)


def hide_menu() -> None:
    popup.hide_menu()
