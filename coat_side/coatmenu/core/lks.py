"""
CoatMenu - import the LKS extension's own radial menus.

LKS keeps each menu as JSON in
``cExtensions/LKS/data/library/radial_menus/*.json`` and resolves its entries in
``utils/radial_menu_config.py``. That resolver defines exactly three forms, and
this module supports the two CoatMenu can honour:

``"$Command"``        a 3DCoat UI command - ``coat.ui.cmd("$Command")``
``"actions/X.py"``    an action script shipped with LKS - run as a script
``module.function``   needs LKS's own importer (``cModules.LKS.``), which only
                      exists inside LKS - such rows are logged and skipped

The menus belong to LKS and the user edits them there, so everything here is
read-only: one CoatMenu submenu per LKS menu, keeping LKS's own labels and order.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from coatmenu.core import catalog
from coatmenu.core.log import log
from coatmenu.core.menu_model import COMMAND, SCRIPT, MenuItem, submenu

MENU_PARTS = ("data", "library", "radial_menus")
NAME_PREFIX = "LKS_Radial_"
MAX_DEPTH = 4


def lks_root() -> str:
    """Where the LKS extension is installed (we only ever read it)."""
    root = catalog.scripts_root()
    return os.path.join(root, "cExtensions", "LKS") if root else ""


def menus_dir() -> str:
    root = lks_root()
    return os.path.join(root, *MENU_PARTS) if root else ""


def short_name(name: str) -> str:
    """``LKS_Radial_Booleans`` -> ``Booleans`` (the panel is the context)."""
    text = (name or "").strip()
    return text[len(NAME_PREFIX):] if text.startswith(NAME_PREFIX) else text


def _is_branch(entry: dict) -> bool:
    return str(entry.get("type") or "").strip().lower() in ("list", "branch")


def _rows(children, root: str, depth: int = 0) -> list[MenuItem]:
    """One level of an LKS menu, mapped onto CoatMenu rows."""
    out: list[MenuItem] = []
    if depth > MAX_DEPTH or not isinstance(children, list):
        return out
    for entry in children:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label") or "").strip()
        action = str(entry.get("action") or "").strip()

        if _is_branch(entry):
            nested = _rows(entry.get("children"), root, depth + 1)
            if label and nested:
                out.append(submenu(label, nested))
            continue

        if not label or not action:
            # LKS writes placeholder rows (label "action", no action) in a fresh
            # menu; there is nothing to run, so they are not imported.
            continue
        if action.startswith("$"):
            out.append(MenuItem(label=label, kind=COMMAND, cid=action))
        elif action.startswith("actions/") and action.endswith(".py"):
            path = os.path.join(root, action.replace("/", os.sep))
            if os.path.isfile(path):
                out.append(MenuItem(label=label, kind=SCRIPT, path=path, cid=path))
            else:
                log(f"lks: action script missing, row skipped: {action}")
        else:
            log(f"lks: action form needs LKS's own importer, row skipped: {action}")
    return out


@dataclass
class LksMenu:
    """One of LKS's radial menus, ready to become a submenu."""

    name: str
    items: list[MenuItem] = field(default_factory=list)


def read_menus() -> list[LksMenu]:
    """Every radial menu LKS has, in file order (never raises)."""
    directory = menus_dir()
    if not directory or not os.path.isdir(directory):
        return []
    root = lks_root()
    out: list[LksMenu] = []
    for filename in sorted(os.listdir(directory)):
        if not filename.lower().endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            log(f"lks: cannot read {filename}: {exc}")
            continue
        if not isinstance(data, dict):
            continue
        title = short_name(str(data.get("name") or os.path.splitext(filename)[0]))
        items = _rows(data.get("items"), root)
        if title and items:
            out.append(LksMenu(name=title, items=items))
    return out
