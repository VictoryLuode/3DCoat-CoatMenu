"""
CoatMenu - runtime list service.

Single owner of the in-memory config and of the two things that keep 3DCoat's
menus in sync with it:

* generated launcher scripts + ``ExtraMenuItems/CoatMenu.xml`` (loaded at startup)
* runtime ``coat.ui.insertInMenu`` calls (visible immediately, so a list added in
  the editor is usable without restarting 3DCoat)
"""
from __future__ import annotations

import os

from coatmenu.core import paths
from coatmenu.core.config import MenuConfig, starter_config
from coatmenu.core.lists_registry import MAIN_MENU_ID, menu_entries, sync
from coatmenu.core.log import log

# Where our menu items appear in 3DCoat's main menu (see menu_sections.txt).
MENU_NAME = "Scripts"

_config: MenuConfig | None = None


# ---------------------------------------------------------------------------
# load / save
# ---------------------------------------------------------------------------


def get_config(reload: bool = False) -> MenuConfig:
    """Current config (starts from the starter config when there is no file)."""
    global _config
    if _config is None or reload:
        _config = MenuConfig.load(paths.config_path())
    return _config


def ensure_config() -> MenuConfig:
    """Load the config, materialise it on first run, and sync menus.

    Called at startup and after the editor saves.
    """
    global _config
    existed = os.path.exists(paths.config_path())
    _config = MenuConfig.load(paths.config_path())
    if not _config.lists:
        _config = starter_config()
    if not existed:
        save_config(_config, register=False)
    else:
        sync_config(_config, register=False)
    return _config


def save_config(config: MenuConfig, register: bool = True) -> dict:
    """Persist the config, regenerate launchers + XML, refresh 3DCoat's menu."""
    global _config
    _config = config
    config.save(paths.config_path())
    return sync_config(config, register=register)


def sync_config(config: MenuConfig, register: bool = True) -> dict:
    info = sync(
        config,
        paths.extension_root(),
        paths.entry_scripts_dir(),
        paths.menu_xml_path(),
    )
    if register:
        info["registered"] = register_menu_items(config)
    log(
        f"sync: {info['lists']} list(s), wrote {len(info['scripts_written'])} launcher(s), "
        f"removed {len(info['scripts_removed'])}, registered {info.get('registered', '-')}"
    )
    return info


# ---------------------------------------------------------------------------
# 3DCoat menu registration
# ---------------------------------------------------------------------------


def register_menu_items(config: MenuConfig) -> int:
    """Insert/refresh our menu items in the running 3DCoat instance.

    Returns how many items were newly inserted. Never raises.
    """
    try:
        import coat  # type: ignore
    except Exception:
        return 0

    inserted = 0
    for menu_id, label, script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir()
    ):
        try:
            coat.ui.addTranslation(menu_id, label)
            if not coat.ui.checkIfMenuItemInserted(menu_id):
                coat.ui.insertInMenu(MENU_NAME, menu_id, script)
                inserted += 1
        except Exception as exc:
            log(f"menu item {menu_id} failed: {exc}")
    return inserted


def unregister_menu_items() -> None:
    """Remove our menu items (used by the editor's 'remove' and by uninstall)."""
    try:
        import coat  # type: ignore
    except Exception:
        return
    ids = [MAIN_MENU_ID] + [lst.hotkey_id for lst in get_config().lists]
    for menu_id in ids:
        try:
            if coat.ui.checkIfMenuItemInserted(menu_id):
                coat.ui.removeCommandFromMenu(menu_id)
        except Exception:
            pass
