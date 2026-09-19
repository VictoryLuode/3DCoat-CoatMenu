"""
CoatMenu - the one and only installer.

Every entry point (``install.cmd``, a shell, 3DCoat's own Python console) calls
this module - there is deliberately no second copy of the install logic.

What it does, all inside ``<Documents>/3DCoat/UserPrefs`` (never the 3DCoat
program folder, never another add-on's files):

1. copies ``coat_side/`` into ``Scripts/cExtensions/CoatMenu/``
2. writes ``Scripts/ExtraMenuItems/CoatMenu.xml`` (absolute script path, because
   3DCoat does not accept relative paths there)
3. appends ``CoatMenu`` to ``Scripts/cExtensions/startup.txt`` (backed up first)

Usage::

    python install.py                 # install / update
    python install.py --uninstall     # remove everything it wrote
    python install.py --documents DIR # use a different user data root (tests)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "coat_side")
EXTENSION_NAME = "CoatMenu"
MENU_ID = "CoatMenu_Show"
MENU_LABEL = "Show CoatMenu"

_MENU_XML = """<ClassArray.ExtraMenuItem>
\t<ExtraMenuItem>
\t\t<MenuPath>Scripts</MenuPath>
\t\t<MenuItem>{menu_id}</MenuItem>
\t\t<inRoom></inRoom>
\t\t<inSection></inSection>
\t\t<Command>script:{script_path}</Command>
\t</ExtraMenuItem>
</ClassArray.ExtraMenuItem>
"""


def default_documents() -> str:
    """Documents folder of the current user (3DCoat's user data lives there)."""
    return os.path.join(os.path.expanduser("~"), "Documents")


def paths(documents: str) -> dict[str, str]:
    scripts = os.path.join(documents, "3DCoat", "UserPrefs", "Scripts")
    return {
        "scripts": scripts,
        "cExtensions": os.path.join(scripts, "cExtensions"),
        "ext": os.path.join(scripts, "cExtensions", EXTENSION_NAME),
        "extra_menu_items": os.path.join(scripts, "ExtraMenuItems"),
        "menu_xml": os.path.join(scripts, "ExtraMenuItems", f"{EXTENSION_NAME}.xml"),
        "startup": os.path.join(scripts, "cExtensions", "startup.txt"),
    }


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


def install(documents: str) -> int:
    p = paths(documents)
    for key in ("cExtensions", "extra_menu_items"):
        os.makedirs(p[key], exist_ok=True)

    # 1. extension files -------------------------------------------------
    os.makedirs(p["ext"], exist_ok=True)
    copied = 0
    for src, rel in _iter_source_files():
        dst = os.path.join(p["ext"], rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    # 2. menu item (absolute path - 3DCoat rejects relative here) --------
    script_path = os.path.join(p["ext"], "actions", "CoatMenu_Show.py").replace("\\", "/")
    with open(p["menu_xml"], "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_MENU_XML.format(menu_id=MENU_ID, script_path=script_path))

    # 3. startup entry --------------------------------------------------
    added = _ensure_startup_entry(p["startup"])

    print(f"CoatMenu installed -> {p['ext']}")
    print(f"  files copied   : {copied}")
    print(f"  menu item      : {p['menu_xml']}  ({MENU_LABEL})")
    print(f"  startup entry  : {'added' if added else 'already present'} in {p['startup']}")
    print("Restart 3DCoat (or restart the extension from Windows > Panels > Extensions),")
    print("then use Scripts > CoatMenu > Show CoatMenu; bind a key to it in")
    print("Preferences > Hotkeys if you want the hold-to-open behaviour.")
    return 0


def _ensure_startup_entry(startup_path: str) -> bool:
    """Append our name to startup.txt. Returns True when a line was added."""
    existing = ""
    if os.path.exists(startup_path):
        with open(startup_path, encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
        backup = f"{startup_path}.bak-coatmenu-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(startup_path, backup)
    lines = [ln.strip() for ln in existing.splitlines()]
    if EXTENSION_NAME in lines:
        return False
    if existing and not existing.endswith("\n"):
        existing += "\n"
    with open(startup_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(existing + EXTENSION_NAME + "\n")
    return True


def uninstall(documents: str) -> int:
    p = paths(documents)
    removed: list[str] = []

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
