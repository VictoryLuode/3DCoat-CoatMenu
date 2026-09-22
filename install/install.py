"""
CoatMenu - the one and only installer.

Every entry point (``install.cmd``, a shell, 3DCoat's own Python console) calls
this module - there is deliberately no second copy of the install logic.

What it does, all inside ``<Documents>/3DCoat/UserPrefs`` (never the 3DCoat
program folder, never another add-on's files):

1. copies ``coat_side/`` into ``Scripts/cExtensions/CoatMenu/``
2. regenerates the per-list launcher scripts and ``Scripts/ExtraMenuItems/CoatMenu.xml``
   from the user's ``data/menus.json`` (absolute script paths - 3DCoat does not
   accept relative ones there)
3. appends ``CoatMenu`` to ``Scripts/cExtensions/startup.txt`` (backed up first)

What it must never do (the menus in that file are the user's, not ours - see
AGENTS.md): rename, reorder, edit or drop a menu he built. A list we shipped is
never "refreshed" once it is in his file - only a *missing* list is added; a
``menus.json`` that cannot be parsed is left exactly as it is, with a dated copy
beside it, instead of being replaced by a starter. And it deletes nothing it did
not write: pruning happens inside ``coatmenu/`` and ``actions/`` only, plus the
retired top-level folders named in ``RETIRED_TOP_LEVEL`` (``ported/`` is one of
them - an earlier version shipped the sculpt actions there).

Usage::

    python install.py                 # install / update
    python install.py --uninstall     # remove everything it wrote
    python install.py --documents DIR # use a different user data root (tests)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "coat_side")
EXTENSION_NAME = "CoatMenu"

# Trees inside the extension folder that belong to the extension: everything under
# them was put there by an install and may be pruned. Anything outside them (the
# user's own scripts, his data/menus.json, 3DCoat's debug stubs) is not ours.
OWNED_TREES = ("coatmenu", "actions")

# Folders a *previous* version of the extension shipped at the top level and no
# longer does. Named explicitly on purpose: an installer may only delete what it
# wrote, never "anything it does not recognise". ``ported`` is the sculpt-action
# tree that used to be a copy of another extension's code - an update removes the
# whole folder, illustrations and .env stubs included, because pruning alone would
# leave everything that is not a .py file behind.
RETIRED_TOP_LEVEL = ("core", "ui", "ported")

if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from coatmenu.core import menus_registry, presets  # noqa: E402
from coatmenu.core.config import MenuConfig, UNREADABLE_TAG, starter_config  # noqa: E402


def _registry_documents() -> list[str]:
    """The Documents folders Windows itself knows about (most reliable first).

    ``User Shell Folders`` is the authoritative one and its value may still
    contain ``%USERPROFILE%``-style variables, so it is expanded; ``Shell Folders``
    holds the already-expanded form and is only a fallback.
    """
    if os.name != "nt":
        return []
    try:
        import winreg
    except Exception:
        return []

    base = r"Software\Microsoft\Windows\CurrentVersion\Explorer"
    out: list[str] = []
    for sub, expand in ((r"User Shell Folders", True), (r"Shell Folders", False)):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + "\\" + sub) as handle:
                value, _kind = winreg.QueryValueEx(handle, "Personal")
        except OSError:
            continue
        path = str(value or "")
        if expand:
            path = os.path.expandvars(path)
        if path:
            out.append(path)
    return out


def data_folder(documents: str) -> str:
    """3DCoat's data folder inside *documents* (``3DCoat``, or a suffixed name).

    Newer versions use ``3DCoat``; an older one may add a suffix, so the folder is
    recognised by holding a ``UserPrefs`` folder rather than by its exact name.
    Returns ``""`` when there is none.
    """
    exact = os.path.join(documents, "3DCoat")
    if os.path.isdir(os.path.join(exact, "UserPrefs")):
        return exact
    try:
        names = sorted(os.listdir(documents))
    except OSError:
        return ""
    for name in names:
        if not name.lower().startswith("3dcoat"):
            continue
        candidate = os.path.join(documents, name)
        if os.path.isdir(os.path.join(candidate, "UserPrefs")):
            return candidate
    return ""


def default_documents() -> str:
    """The Documents folder that holds 3DCoat's user data.

    Looked up rather than assumed. 3DCoat lets the user pick its data folder on
    first run, and Windows itself often redirects Documents into OneDrive (3DCoat's
    own API docs use ``C:/Users\\<user>\\OneDrive\\Documents/3DCoat/...`` as the
    example). The registry answers first - it is where a Documents folder that was
    moved to another drive is recorded - then the usual places, and every candidate
    is checked for 3DCoat's data folder so a Documents folder 3DCoat never touches
    is not mistaken for the real one.

    ``COATMENU_DOCUMENTS`` wins over the guess; ``--documents`` beats everything.
    """
    explicit = os.environ.get("COATMENU_DOCUMENTS")
    if explicit:
        return explicit

    home = os.path.expanduser("~")
    profile = os.environ.get("USERPROFILE") or home
    candidates = list(_registry_documents())
    candidates += [
        os.path.join(home, "Documents"),
        os.path.join(profile, "Documents"),
    ]
    try:
        for name in sorted(os.listdir(profile)):
            if name.lower().startswith("onedrive"):
                candidates.append(os.path.join(profile, name, "Documents"))
    except OSError:
        pass
    candidates += [
        os.path.join(home, "OneDrive", "Documents"),
        os.path.join(home, "OneDrive - Personal", "Documents"),
    ]

    seen: set[str] = set()
    for candidate in candidates:
        candidate = os.path.normpath(candidate)
        if candidate in seen:
            continue
        seen.add(candidate)
        if data_folder(candidate):
            return candidate
    # Nothing looked familiar: hand back the plain Documents and let install() warn.
    return os.path.normpath(candidates[0]) if candidates else os.path.join(home, "Documents")


def paths(documents: str) -> dict[str, str]:
    data = data_folder(documents) or os.path.join(documents, "3DCoat")
    scripts = os.path.join(data, "UserPrefs", "Scripts")
    return {
        "data": data,
        "scripts": scripts,
        "cExtensions": os.path.join(scripts, "cExtensions"),
        "ext": os.path.join(scripts, "cExtensions", EXTENSION_NAME),
        "extra_menu_items": os.path.join(scripts, "ExtraMenuItems"),
        "menu_xml": os.path.join(scripts, "ExtraMenuItems", f"{EXTENSION_NAME}.xml"),
        "startup": os.path.join(scripts, "cExtensions", "startup.txt"),
    }


def _owned(rel_dir: str) -> bool:
    """True for a path we may prune: inside one of the extension's own trees.

    ``rel_dir`` is relative to the extension folder and uses forward slashes;
    ``.`` is the extension root itself, which is never ours to clean.
    """
    if rel_dir in (".", ""):
        return False
    return rel_dir.split("/")[0] in OWNED_TREES


def _iter_source_files() -> list[tuple[str, str]]:
    """(absolute source, relative destination) for every file we ship."""
    out: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(SOURCE_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "tests", ".vscode")]
        for name in sorted(filenames):
            if name.endswith((".pyc", ".pyo")) or name.startswith("."):
                continue
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, SOURCE_DIR)
            out.append((src, rel))
    return out


def _prune_stale(ext_dir: str, shipped: set[str]) -> list[str]:
    """Delete modules that a previous version left behind.

    Only inside the trees the extension owns (``coatmenu/`` and ``actions/``): a
    ``.py`` somewhere else in the extension folder was not put
    there by an install, so it is the user's and stays - as does ``data/`` (his
    config) and ``actions/menus/`` (generated launchers, managed elsewhere).
    """
    removed: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ext_dir):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "data")]
        rel_dir = os.path.relpath(dirpath, ext_dir).replace("\\", "/")
        if not _owned(rel_dir):
            continue
        for name in filenames:
            if not name.endswith(".py"):
                continue
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if rel in shipped or rel.startswith(("actions/menus/", "actions/shortcuts/")):
                continue
            try:
                os.remove(os.path.join(dirpath, name))
                removed.append(rel)
            except OSError:
                pass
    return removed


def _remove_stale_dirs(ext_dir: str) -> list[str]:
    """Delete folders a *previous* version of the extension shipped and no longer does.

    An earlier version shipped ``core/`` and ``ui/`` at the top level - and
    ``ported/``, which held its sculpt actions - and 3DCoat had already generated
    its own ``.env``/``.vscode`` debug stubs inside them, so "remove if empty"
    would never get rid of them. Only those known names go: an unknown folder in
    here may well be something of the user's, and an installer has no business
    deleting what it did not write.
    """
    removed: list[str] = []
    keep_top = {"data", "actions", "coatmenu"}

    for name in sorted(os.listdir(ext_dir)):
        path = os.path.join(ext_dir, name)
        if not os.path.isdir(path):
            continue
        if name == "__pycache__":
            shutil.rmtree(path, ignore_errors=True)
            removed.append("__pycache__/")
        elif name in RETIRED_TOP_LEVEL:
            shutil.rmtree(path, ignore_errors=True)
            removed.append(f"{name}/")
        # Everything else (our layout folders, 3DCoat's dotfolders, anything the
        # user added) is left alone. `keep_top` documents the layout for readers.
        elif name in keep_top or name.startswith("."):
            continue

    package = os.path.join(ext_dir, "coatmenu")
    if os.path.isdir(package):
        for name in sorted(os.listdir(package)):
            path = os.path.join(package, name)
            if not os.path.isdir(path):
                continue
            if name == "__pycache__":
                shutil.rmtree(path, ignore_errors=True)
            elif name not in ("core", "ui"):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(f"coatmenu/{name}/")

    # A previous layout kept the launchers in actions/lists/; they live in
    # actions/menus/ now, and the old folder would otherwise linger with stale
    # copies in it.
    for old in ("lists",):
        path = os.path.join(ext_dir, "actions", old)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(f"actions/{old}/")

    # ...and finally any folder left empty anywhere below our own trees.
    for dirpath, dirnames, filenames in os.walk(ext_dir, topdown=False):
        if dirnames or filenames:
            continue
        rel = os.path.relpath(dirpath, ext_dir).replace("\\", "/")
        if rel in (".", "data", "actions", "actions/menus", "actions/shortcuts",
                   "coatmenu", "coatmenu/core", "coatmenu/ui"):
            continue
        if not _owned(rel):
            # Not ours: an empty folder of the user's is still his.
            continue
        try:
            os.rmdir(dirpath)
            removed.append(f"{rel}/")
        except OSError:
            pass
    return removed


def _uses_old_key(path: str) -> bool:
    """True for a config written before the terminology pass (had a "lists" key)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return False
    return isinstance(data, dict) and "menus" not in data


def _unreadable(path: str) -> str:
    """The path itself when it exists but cannot be parsed as JSON, else "".

    A config we cannot read is the one case where writing "a fresh starter" would
    destroy menus the user built by hand - so the installer refuses to write it
    instead. The file is usually recoverable (a stray edit, a half-synced copy);
    replacing it silently is not.
    """
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as fh:
            json.load(fh)
    except Exception:
        return path
    return ""


def _load_or_create_config(ext_dir: str, documents: str) -> MenuConfig:
    """Config from the installed copy when it exists, else a fresh starter."""
    path = os.path.join(ext_dir, "data", "menus.json")
    legacy = os.path.join(ext_dir, "data", "lists.json")
    if not os.path.exists(path) and os.path.exists(legacy):
        try:
            # The terminology pass renamed the file; move it rather than leaving
            # two configs behind.
            os.replace(legacy, path)
        except OSError:
            path = legacy
    if os.path.exists(path):
        config = MenuConfig.load(path)
        if config.menus:
            return config
    return starter_config(documents)


def install(documents: str) -> int:
    p = paths(documents)
    if not data_folder(documents):
        # Better a loud warning than a silent install into a folder 3DCoat never
        # reads - its data folder can live anywhere (chosen on first run, or
        # Documents redirected into OneDrive), and a portable install keeps
        # UserPrefs inside the program folder.
        print(f"CoatMenu: no 3DCoat data folder under {documents}")
        print("  Let 3DCoat start once, then pass its data folder explicitly -")
        print("  the folder that holds UserPrefs (see its executable.txt):")
        print('    python install.py --documents "D:\\path\\to\\Documents"')
    for key in ("cExtensions", "extra_menu_items"):
        os.makedirs(p[key], exist_ok=True)

    # 1. extension files -------------------------------------------------
    os.makedirs(p["ext"], exist_ok=True)
    files = _iter_source_files()
    copied = 0
    for src, rel in files:
        dst = os.path.join(p["ext"], rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    stale = _prune_stale(p["ext"], {rel.replace("\\", "/") for _src, rel in files})
    stale += _remove_stale_dirs(p["ext"])

    # 2. launcher scripts + menu XML from the user's config ---------------
    config_path = os.path.join(p["ext"], "data", "menus.json")
    legacy_path = os.path.join(p["ext"], "data", "lists.json")
    broken = _unreadable(legacy_path) or _unreadable(config_path)
    config = _load_or_create_config(p["ext"], documents)
    # Built-in presets land once - a *missing* list is added, never an existing
    # one touched, and never into a config we cannot read (that one is left
    # exactly alone; see `broken`).
    added_presets = [] if broken else presets.install_presets(config)
    rewrite = (not broken and
               (added_presets or not os.path.exists(config_path) or _uses_old_key(config_path)))
    for candidate in (config_path, legacy_path):
        if rewrite and os.path.exists(candidate):
            _backup(candidate, "coatmenu")
    if rewrite:
        # Written when the file is new, a missing preset was added, or the file
        # still carries the pre-terminology key. Never over an unreadable config,
        # and never to "tidy up" a readable one.
        config.save(config_path)
    info = menus_registry.sync(
        config,
        p["ext"],
        os.path.join(p["ext"], "actions", "menus"),
        p["menu_xml"],
    )
    leftovers = clean_per_entry_xml(p["extra_menu_items"])
    retired = clean_retired_dirs(p["ext"])

    # 3. startup entry --------------------------------------------------
    added = _ensure_startup_entry(p["startup"])

    print(f"CoatMenu installed -> {p['ext']}")
    print(f"  files copied   : {copied}")
    if broken:
        quarantine = f"{broken}{UNREADABLE_TAG}{time.strftime('%Y%m%d-%H%M%S')}"
        try:
            shutil.copy2(broken, quarantine)
        except OSError:
            quarantine = ""
        print(f"  ! unreadable   : {broken}")
        print("                   left as it is - nothing in it was rewritten or removed")
        if quarantine:
            print(f"                   a copy is at {quarantine}")
        print("                   fix or move the file, then run install again")
    if stale:
        print(f"  stale removed  : {', '.join(stale)}")
    if leftovers:
        print(f"  cleaned up     : {len(leftovers)} per-entry XML file(s) left by insertInMenu")
    if retired:
        print(f"  removed        : {', '.join(retired)} (no longer used)")
    print(f"  menus          : {info['menus']} ({', '.join(lst.name for lst in config.menus)})")
    print(f"  menu items     : 3 fixed in {p['menu_xml']}, "
          f"{info['menus']} inserted at runtime")
    print(f"  startup entry  : {'added' if added else 'already present'} in {p['startup']}")
    print("Restart 3DCoat (or restart the extension from Windows > Panels > Extensions),")
    print("then use Scripts > CoatMenu > Show CoatMenu. To give a menu its own key,")
    print("hover that entry in Scripts > CoatMenu and press END, then press the keys")
    print("you want - that is 3DCoat's own way of assigning a hotkey. The menu stays")
    print("open when you release the key: pick an entry, click away, or press Esc.")
    return 0


def clean_retired_dirs(ext_dir: str) -> list[str]:
    """Delete folders an earlier version generated and this one has no use for.

    ``actions/shortcuts/`` held one launcher per keyed row, from when the plugin
    tried to hand out hotkeys itself. It does not any more - binding is done in
    3DCoat (hover an entry, press END) - so the folder would only linger.
    """
    retired = ["shortcuts"]
    removed: list[str] = []
    for name in retired:
        path = os.path.join(ext_dir, "actions", name)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(f"actions/{name}/")
    return removed


def clean_per_entry_xml(extra_menu_items_dir: str) -> list[str]:
    """Remove the ``CoatMenu_<id>.xml`` files 3DCoat writes for ``insertInMenu``.

    Calling ``coat.ui.insertInMenu`` made 3DCoat persist one XML per entry next to
    our own ``CoatMenu.xml``. It reads those files at startup too, so an entry we
    also register through the menu API would be listed twice.

    Only ``CoatMenu_*.xml`` is touched: ``CoatBridge*`` and ``LKS_*`` in the same
    folder belong to other add-ons.
    """
    removed: list[str] = []
    try:
        names = os.listdir(extra_menu_items_dir)
    except OSError:
        return removed
    for name in names:
        if not name.startswith(f"{EXTENSION_NAME}_") or not name.endswith(".xml"):
            continue
        path = os.path.join(extra_menu_items_dir, name)
        try:
            os.remove(path)
            removed.append(path)
        except OSError:
            pass
    return removed


def _backup(path: str, tag: str, keep: int = 3) -> str | None:
    """Back a file up, but only when it actually differs from the last backup.

    The first version copied on every run, so a month of reinstalling left 88
    ``.bak-*`` files behind. Now the copy happens only when the content changed,
    and older backups beyond ``keep`` are pruned.
    """
    if not os.path.isfile(path):
        return None
    folder, name = os.path.split(path)
    prefix = f"{name}.bak-{tag}-"

    with open(path, "rb") as fh:
        current = fh.read()

    existing = sorted(n for n in os.listdir(folder) if n.startswith(prefix))
    if existing:
        newest = os.path.join(folder, existing[-1])
        try:
            with open(newest, "rb") as fh:
                if fh.read() == current:
                    return None  # nothing changed, no new backup
        except OSError:
            pass

    backup = os.path.join(folder, f"{prefix}{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)

    for stale in sorted(n for n in os.listdir(folder) if n.startswith(prefix))[:-keep]:
        try:
            os.remove(os.path.join(folder, stale))
        except OSError:
            pass
    return backup


def _ensure_startup_entry(startup_path: str) -> bool:
    """Append our name to startup.txt. Returns True when a line was added."""
    existing = ""
    if os.path.exists(startup_path):
        with open(startup_path, encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
    lines = [ln.strip() for ln in existing.splitlines()]
    if EXTENSION_NAME in lines:
        return False
    if existing:
        _backup(startup_path, "coatmenu")
    if existing and not existing.endswith("\n"):
        existing += "\n"
    with open(startup_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(existing + EXTENSION_NAME + "\n")
    return True


def uninstall(documents: str) -> int:
    p = paths(documents)
    removed: list[str] = []

    # Keep the user's menus - an uninstall should not throw away their work.
    config_path = os.path.join(p["ext"], "data", "menus.json")
    if os.path.exists(config_path):
        backup = os.path.join(documents, "3DCoat", f"{EXTENSION_NAME}-menus-backup.json")
        try:
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.copy2(config_path, backup)
            removed.append(f"your lists were backed up to {backup}")
        except OSError:
            pass

    if os.path.isdir(p["ext"]):
        shutil.rmtree(p["ext"], ignore_errors=True)
        removed.append(p["ext"])
    if os.path.exists(p["menu_xml"]):
        os.remove(p["menu_xml"])
        removed.append(p["menu_xml"])

    if os.path.exists(p["startup"]):
        with open(p["startup"], encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        kept = [ln for ln in lines if ln.strip() != EXTENSION_NAME]
        if len(kept) != len(lines):
            with open(p["startup"], "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(kept) + ("\n" if kept else ""))
            removed.append(f"{p['startup']} (entry removed)")

    print("CoatMenu removed:")
    for item in removed or ["nothing was installed"]:
        print(f"  - {item}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install or remove the CoatMenu 3DCoat extension.")
    parser.add_argument("--uninstall", action="store_true", help="remove CoatMenu files")
    parser.add_argument("--documents", default=None, help="user Documents folder (tests)")
    args = parser.parse_args(argv)

    documents = args.documents or default_documents()
    if not os.path.isdir(documents):
        print(f"error: Documents folder not found: {documents}", file=sys.stderr)
        return 2
    return uninstall(documents) if args.uninstall else install(documents)


if __name__ == "__main__":
    sys.exit(main())
