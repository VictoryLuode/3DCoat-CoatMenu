"""
Headless test harness: a fake ``coat`` module.

3DCoat's API is unavailable outside the application, so tests inject this in
place of the real thing. It records every call so a test can assert that a click
really did execute the command it was supposed to.
"""
from __future__ import annotations

import os
import sys
import types


class FakeCoat:
    def __init__(self, documents: str, install_root: str | None = None):
        self.calls: list[tuple[str, str]] = []
        self.translations: dict[str, str] = {}
        self.menu_items: dict[str, tuple[str, str]] = {}
        # 3DCoat's own menu API (top-level coat.menu_item / coat.menu_hotkey),
        # which is how the one-per-menu entries and their keys get registered.
        self.menu_api: list[str] = []
        self.hotkey_api: list[tuple[str, int, int, int]] = []
        self._documents = documents
        self._install = install_root or os.path.join(documents, "3DCoat-Install")
        self.ui = types.SimpleNamespace(
            cmd=self._cmd,
            presentInUI=lambda _id: True,
            addTranslation=self._add_translation,
            insertInMenu=self._insert_in_menu,
            checkIfMenuItemInserted=self._check_menu_item,
            removeCommandFromMenu=self._remove_command_from_menu,
        )
        self.io = types.SimpleNamespace(
            documents=lambda: self._documents,
            installPath=lambda: self._install,
            executeScript=self._script,
            step=lambda _n: 0,
        )
        self.settings = types.SimpleNamespace(
            getBool=lambda _k, default=False: default,
            getInt=lambda _k, default=0: default,
        )
        self.dialog = types.SimpleNamespace()

    def _cmd(self, cid, callback=None):
        self.calls.append(("cmd", str(cid)))
        if callback:
            callback()

    def _menu_item(self, item_id):
        self.menu_api.append(str(item_id))
        return True

    def _menu_hotkey(self, key, shift, ctrl, alt):
        self.hotkey_api.append((str(key), int(shift), int(ctrl), int(alt)))
        return True

    def _add_translation(self, key, text):
        self.translations[str(key)] = str(text)
        return True

    def _insert_in_menu(self, menu, menu_id, script_path):
        self.menu_items[str(menu_id)] = (str(menu), str(script_path))
        return True

    def _check_menu_item(self, menu_id):
        return str(menu_id) in self.menu_items

    def _remove_command_from_menu(self, menu_id):
        self.menu_items.pop(str(menu_id), None)
        return True

    def _script(self, path):
        self.calls.append(("script", str(path)))

    def commands_run(self) -> list[str]:
        return [arg for kind, arg in self.calls if kind == "cmd"]

    def scripts_run(self) -> list[str]:
        return [arg for kind, arg in self.calls if kind == "script"]


def install_fake_coat(documents: str | None = None, source_dir: str | None = None,
                      install_root: str | None = None):
    """Put a fake ``coat`` on sys.modules and return it.

    ``source_dir`` (the coat_side folder) is added to sys.path so ``coatmenu.*``
    imports exactly as it does inside 3DCoat. ``install_root`` stands in for the
    3DCoat program folder (menu definitions, English.xml).
    """
    documents = documents or os.path.join(os.environ.get("TEMP", "."), "coatmenu-fake-docs")
    if source_dir and source_dir not in sys.path:
        sys.path.insert(0, source_dir)

    fake = FakeCoat(documents, install_root)
    module = types.ModuleType("coat")
    module.ui = fake.ui
    module.io = fake.io
    module.settings = fake.settings
    module.dialog = fake.dialog
    module.menu_item = fake._menu_item
    module.menu_hotkey = fake._menu_hotkey
    sys.modules["coat"] = module
    return fake
