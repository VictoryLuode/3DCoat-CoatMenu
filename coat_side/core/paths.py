"""
CoatMenu - where things live.

All of this is derived at runtime inside 3DCoat: the extension root is inferred
from this file's own location, so the same code works from the repository, from
the installed copy under ``Scripts/cExtensions/CoatMenu`` and from a test tree.
"""
from __future__ import annotations

import os

MENU_XML_NAME = "CoatMenu.xml"


def extension_root() -> str:
    """``<ext>`` - the folder holding CoatMenu.py, core/, ui/, actions/."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir() -> str:
    """User data (never shipped, never overwritten by the installer).

    ``COATMENU_DATA_DIR`` overrides it - used by the tests so they never write
    into the extension folder they are testing.
    """
    override = os.environ.get("COATMENU_DATA_DIR")
    if override:
        return override
    return os.path.join(extension_root(), "data")


def config_path() -> str:
    return os.path.join(data_dir(), "lists.json")


def entry_scripts_dir() -> str:
    """One thin launcher script per list (what the menu items point at)."""
    return os.path.join(extension_root(), "actions", "lists")


def documents() -> str:
    """User Documents folder - inside 3DCoat this comes from the host API."""
    try:
        import coat  # type: ignore
        return str(coat.io.documents())
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Documents")


def scripts_dir(documents_path: str | None = None) -> str:
    return os.path.join(documents_path or documents(), "3DCoat", "UserPrefs", "Scripts")


def menu_xml_path(documents_path: str | None = None) -> str:
    return os.path.join(scripts_dir(documents_path), "ExtraMenuItems", MENU_XML_NAME)
