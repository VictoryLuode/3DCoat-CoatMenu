"""
CoatMenu - command catalog.

Sources of "things you can put in a menu":

1. ``Options_Hotkeys.xml`` - every command 3DCoat knows about, already tagged
   with the room it belongs to (this is what the hotkey editor itself uses).
2. ``CustomMenu/**/*.command`` - 3DCoat's own custom-menu files: three lines
   (display name / command id / tooltip).
3. Scripts under ``UserPrefs/Scripts``.
4. ``CMD.pyi`` - the module-level command functions.

Everything is read-only. Nothing here writes to the user's files.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .log import log


@dataclass
class CommandEntry:
    """One catalog entry."""

    cid: str          # identifier handed to coat.ui.cmd() ("$" prefix added at run time)
    label: str        # human readable
    room: str = ""    # "" = global
    source: str = ""  # hotkeys | custommenu | script | cmdpy

    @property
    def cmd_string(self) -> str:
        return self.cid if self.cid.startswith("$") else "$" + self.cid


def _documents() -> str:
    try:
        import coat  # type: ignore
        return str(coat.io.documents())
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Documents")


def hotkeys_path() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "Preferences", "Options_Hotkeys.xml")


def custom_menu_root() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "CustomMenu")


def scripts_root() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "Scripts")


def read_hotkey_commands(path: str | None = None) -> list[CommandEntry]:
    """Parse every ``<OneHotKey>`` into a unique command entry.

    Returns entries sorted by room then id. Malformed file -> empty list, never
    an exception (the file is user owned and gets hand-edited).
    """
    path = path or hotkeys_path()
    out: dict[str, CommandEntry] = {}
    try:
        tree = ET.parse(path)
    except Exception as exc:
        log(f"catalog: cannot read hotkeys file {path}: {exc}")
        return []
    for node in tree.getroot().iter("OneHotKey"):
        cid = (node.findtext("ID") or "").strip()
        if not cid or cid in out:
            continue
        room = (node.findtext("Room") or "").strip()
        out[cid] = CommandEntry(cid=cid, label=cid, room=room, source="hotkeys")
    return sorted(out.values(), key=lambda e: (e.room, e.cid))


def read_custom_menu_commands(root: str | None = None) -> list[CommandEntry]:
    """Read 3DCoat's ``*.command`` files (name / command id / tooltip)."""
    root = root or custom_menu_root()
    out: list[CommandEntry] = []
    if not os.path.isdir(root):
        return out
    for dirpath, _dirnames, filenames in os.walk(root):
        section = os.path.relpath(dirpath, root).replace("\\", "/")
        for name in filenames:
            if not name.lower().endswith(".command"):
                continue
            try:
                with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                    lines = [ln.strip() for ln in fh.read().splitlines()]
            except Exception:
                continue
            label = lines[0] if lines else name
            cid = re.sub(r"^\$", "", lines[1]) if len(lines) > 1 and lines[1] else ""
            if not cid:
                continue
            out.append(CommandEntry(cid=cid, label=label or cid, room=section, source="custommenu"))
    return out


def read_script_commands(root: str | None = None, limit: int = 400) -> list[CommandEntry]:
    """List ``UserPrefs/Scripts`` python files as menu-item candidates."""
    root = root or scripts_root()
    out: list[CommandEntry] = []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".vscode", ".tools")]
        for name in sorted(filenames):
            if not name.endswith(".py") or name.startswith("_"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace("\\", "/")
            if rel.startswith("cExtensions/") and "/tests/" in rel:
                continue
            out.append(CommandEntry(cid=os.path.join(dirpath, name), label=rel, source="script"))
            if len(out) >= limit:
                return out
    return out


def describe_counts() -> str:
    """One-line summary used by the demo panel."""
    return (
        f"hotkeys={len(read_hotkey_commands())} "
        f"custommenu={len(read_custom_menu_commands())} "
        f"scripts={len(read_script_commands())}"
    )
