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
from coatmenu.core.menus_registry import (
    MAIN_MENU_ID,
    legacy_hotkey_ids,
    menu_entries,
    sync,
)
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


def _migrate_config_name() -> None:
    """Rename a pre-terminology ``lists.json`` to ``menus.json`` (once).

    A rename rather than a copy: the config then exists under exactly one name, so
    there is no chance of two files drifting apart. If the rename fails the old
    file is untouched and the next start tries again.
    """
    new = paths.config_path()
    old = paths.legacy_config_path()
    if not os.path.exists(old) or os.path.exists(new):
        return
    try:
        os.replace(old, new)
        log("migrated lists.json -> menus.json")
    except OSError as exc:
        log(f"could not rename {old} -> {new}: {exc}")


def ensure_config() -> MenuConfig:
    """Load the config, materialise it on first run, and sync menus.

    Called at startup and after the editor saves.
    """
    global _config
    _migrate_config_name()
    existed = os.path.exists(paths.config_path())
    _config = MenuConfig.load(paths.config_path())
    if not _config.menus:
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
        f"sync: {info['menus']} menu(s), wrote {len(info['scripts_written'])} launcher(s), "
        f"removed {len(info['scripts_removed'])}, "
        f"registered {info.get('registered', '-')}"
    )
    return info


# ---------------------------------------------------------------------------
# 3DCoat menu registration
# ---------------------------------------------------------------------------


def register_menu_items(config: MenuConfig) -> int:
    """Insert/refresh every menu item in the running 3DCoat instance.

    Runtime insertion via ``coat.ui.insertInMenu`` is the path that is known to
    work here: it is how these entries got into the Scripts menu in the first
    place. A key (if the editor set one) goes immediately after its own item,
    because ``coat.menu_hotkey`` applies to the entry it follows - never to an
    entry that was already there, whose key is not ours to decide.

    Returns how many items were newly inserted. Never raises.
    """
    try:
        import coat  # type: ignore
    except Exception:
        return 0

    inserted = 0
    # Drop entries left behind by earlier id schemes first, otherwise a menu shows
    # up twice in 3DCoat's Scripts list for the rest of the session.
    for menu_id in legacy_hotkey_ids(config):
        try:
            if coat.ui.checkIfMenuItemInserted(menu_id):
                coat.ui.removeCommandFromMenu(menu_id)
                log(f"removed legacy menu item {menu_id}")
        except Exception as exc:
            log(f"legacy menu item {menu_id} not removed: {exc}")

    for menu_id, label, script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir()
    ):
        try:
            coat.ui.addTranslation(menu_id, label)
            if coat.ui.checkIfMenuItemInserted(menu_id):
                continue
            coat.ui.insertInMenu(MENU_NAME, menu_id, script)
            inserted += 1
        except Exception as exc:
            log(f"menu item {menu_id} failed: {exc}")
    # CoatMenu deliberately does not touch hotkeys: binding is done in 3DCoat -
    # hover the entry and press END. Attaching a key from here was measured to be
    # impossible on this build (entries added at runtime never reach the hotkey
    # system) and actively harmful (3DCoat rewrites them with an empty <Code>).
    log(f"menu items: inserted={inserted}")
    return inserted


def unregister_menu_items() -> None:
    """Remove our menu items (used by the editor's 'remove' and by uninstall)."""
    try:
        import coat  # type: ignore
    except Exception:
        return
    ids = [MAIN_MENU_ID] + [lst.hotkey_id for lst in get_config().menus]
    ids += legacy_hotkey_ids(get_config())
    for menu_id in ids:
        try:
            if coat.ui.checkIfMenuItemInserted(menu_id):
                coat.ui.removeCommandFromMenu(menu_id)
        except Exception:
            pass
