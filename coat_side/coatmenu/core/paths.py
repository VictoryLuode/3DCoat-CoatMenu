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
    """``<ext>`` - the folder holding CoatMenu.py, coatmenu/, actions/.

    (``coatmenu/core/paths.py`` -> coatmenu/core -> coatmenu -> <ext>.)
    """
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )


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
    return os.path.join(data_dir(), "menus.json")


def legacy_config_path() -> str:
    """The config was called lists.json before the terminology pass."""
    return os.path.join(data_dir(), "lists.json")


def entry_scripts_dir() -> str:
    """One thin launcher script per menu (what the menu items point at)."""
    return os.path.join(extension_root(), "actions", "menus")


def documents() -> str:
    """User Documents folder - inside 3DCoat this comes from the host API."""
    try:
        import coat  # type: ignore
        return str(coat.io.documents(""))
    except Exception:
        pass
    try:
        import coat  # type: ignore
        return str(coat.io.documents())  # older bridge: no argument
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Documents")


def _as_data_root(path: str) -> str:
    """*path* itself when it holds ``UserPrefs``, else its ``3DCoat*`` child.

    Accepts both spellings of the question - the data folder, and the Documents
    folder that contains it - because which one a host API hands back is not
    something we can rely on.
    """
    if not path or not os.path.isdir(path):
        return ""
    if os.path.isdir(os.path.join(path, "UserPrefs")):
        return path
    try:
        names = sorted(os.listdir(path))
    except OSError:
        return ""
    for name in names:
        if not name.lower().startswith("3dcoat"):
            continue
        nested = os.path.join(path, name)
        if os.path.isdir(os.path.join(nested, "UserPrefs")):
            return nested
    return ""


def data_root() -> str:
    """3DCoat's user data folder - the one that holds ``UserPrefs``.

    Asked of the host rather than assumed. The data folder is chosen on first run
    and can be anywhere (Documents itself is often redirected into OneDrive), and
    guessing wrong is not a small thing: the extension would read and write a
    folder 3DCoat never looks at, so its menus would simply never appear.
    ``coat.io.dataPath()`` is the documented answer; the other call is tried
    because a bridge without it would leave us guessing. Every candidate has to
    show a ``UserPrefs`` folder to win, and the plain-Documents fallbacks are only
    used when there is no host to ask (the standalone installer) - so inside
    3DCoat, or in a test with a fake host, we never wander off to a folder that
    belongs to somebody else's machine.

    ``COATMENU_DATA_ROOT`` overrides the whole thing (the tests use it).
    """
    override = os.environ.get("COATMENU_DATA_ROOT")
    if override:
        return override

    home = os.path.expanduser("~")
    host_documents = ""
    candidates: list[str] = []
    try:
        import coat  # type: ignore
    except Exception:
        coat = None  # type: ignore
    if coat is not None:
        host_documents = documents()
        for call in (lambda: coat.io.dataPath(), lambda: coat.io.documents("")):
            try:
                candidates.append(str(call()))
            except Exception:
                pass
        candidates.append(host_documents)
    else:
        host_documents = os.path.join(home, "Documents")
        candidates += [
            os.path.join(home, "OneDrive", "Documents"),
            os.path.join(home, "OneDrive - Personal", "Documents"),
        ]
    candidates.append(os.path.join(host_documents, "3DCoat"))

    seen: set[str] = set()
    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        found = _as_data_root(candidate)
        if found:
            return found
    # Nothing there yet (a machine where 3DCoat has not run): the usual place.
    return os.path.join(host_documents or os.path.join(home, "Documents"), "3DCoat")


def scripts_dir(data_root_path: str | None = None) -> str:
    """``<data>/UserPrefs/Scripts`` - the folder 3DCoat loads scripts from."""
    root = data_root_path or data_root()
    return os.path.join(_as_data_root(root) or root, "UserPrefs", "Scripts")


def menu_xml_path(data_root_path: str | None = None) -> str:
    return os.path.join(scripts_dir(data_root_path), "ExtraMenuItems", MENU_XML_NAME)
