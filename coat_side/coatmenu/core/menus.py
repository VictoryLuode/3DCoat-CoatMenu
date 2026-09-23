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
from coatmenu.core.config import (
    MenuConfig,
    quarantine_unreadable,
    config_readable,
    starter_config,
)
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
    path = paths.config_path()
    if not config_readable(path):
        # Never trade his file for a starter: a config we cannot parse is moved
        # aside, and the save below writes a fresh one at the canonical path. He
        # gets a warning in the log (and in the doctor) instead of silent loss.
        moved = quarantine_unreadable(path)
        log(f"menus.json unreadable - kept at {moved or path}; starting from a starter")
    existed = os.path.exists(path)
    _config = MenuConfig.load(path)
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
        # Menus that are gone have to leave the *running* 3DCoat too: deleting the
        # file only takes effect at the next start, and he should not have to
        # restart to be rid of a menu he just deleted.
        info["unregistered"] = drop_menu_items(info.get("extra_ids_removed", []))
        info["registered"] = register_menu_items(config)
    log(
        f"sync: {info['menus']} menu(s), wrote {len(info['scripts_written'])} launcher(s), "
        f"removed {len(info['scripts_removed'])}, "
        f"cleaned {len(info.get('extra_items_removed', []))} stale entry file(s), "
        f"registered {info.get('registered', '-')}"
    )
    return info


# ---------------------------------------------------------------------------
# 3DCoat menu registration
# ---------------------------------------------------------------------------


def _is_menu_item_inserted(coat, menu_id: str) -> bool:
    """Whether 3DCoat currently lists this menu item (never raises)."""
    try:
        return bool(coat.ui.checkIfMenuItemInserted(menu_id))
    except Exception:
        return False


def drop_menu_items(menu_ids: list[str]) -> int:
    """Take menu items out of the running 3DCoat; returns how many went.

    The files are pruned separately (``menus_registry.prune_persisted_menu_items``).
    An id that is not in the menu is a no-op, so this is safe to call with ids
    that were only ever written to disk.
    """
    if not menu_ids:
        return 0
    try:
        import coat  # type: ignore
    except Exception:
        return 0
    dropped = 0
    for menu_id in menu_ids:
        try:
            coat.ui.removeCommandFromMenu(menu_id)
            dropped += 1
            log(f"removed menu item {menu_id}")
        except Exception as exc:
            log(f"menu item {menu_id} not removed: {exc}")
    return dropped


def register_menu_items(config: MenuConfig) -> int:
    """Insert/refresh every menu item in the running 3DCoat instance.

    Runtime insertion via ``coat.ui.insertInMenu`` is the path that is known to
    work here: it is how these entries get into the Scripts menu. Keys are not
    touched - binding one is 3D-Coat's own job (hover the entry, press END).

    Returns how many items were newly inserted. Never raises.
    """
    try:
        import coat  # type: ignore
    except Exception:
        return 0

    inserted = 0
    # Drop entries left behind by earlier id schemes first, otherwise a menu shows
    # up twice in 3DCoat's Scripts list for the rest of the session.
    drop_menu_items([menu_id for menu_id in legacy_hotkey_ids(config)
                     if _is_menu_item_inserted(coat, menu_id)])

    # The three fixed entries are carried by ``ExtraMenuItems/CoatMenu.xml``, which
    # 3DCoat reads whether or not this extension loads: they are *not* inserted at
    # runtime. 3DCoat persists every insertion as its own file, and an id living in
    # both that file and CoatMenu.xml is listed twice (which is exactly what used to
    # happen). Their translation still goes in, so they show their readable name.
    fixed_ids = [menu_id for menu_id, _label, _script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir(), include="fixed")]
    drop_menu_items([menu_id for menu_id in fixed_ids
                     if _is_menu_item_inserted(coat, menu_id)])
    for menu_id, label, _script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir(), include="fixed"
    ):
        try:
            coat.ui.addTranslation(menu_id, label)
        except Exception as exc:
            log(f"translation for {menu_id} failed: {exc}")

    for menu_id, label, script in menu_entries(
        config, paths.extension_root(), paths.entry_scripts_dir(), include="menus"
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
