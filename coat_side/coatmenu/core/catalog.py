"""
CoatMenu - command catalog.

Where the entries you can put in a menu come from:

1. **3DCoat's own menu definitions** - ``<install>/UserPrefs/StdScripts/cTemplates``
   (``MainMenu/*.py`` plus the room/tool scripts) call ``menu_item("<id>")`` for
   every menu entry 3DCoat has: ~600 command ids, authoritative, and living in the
   program folder so they never get corrupted.
2. ``Options_Hotkeys.xml`` - the ids that participate in 3DCoat's hotkey system,
   with the room each belongs to. **Parsed leniently on purpose**: 3DCoat rewrites
   this file with un-escaped ``&`` characters, which makes a strict XML parser
   reject the whole document (which is why this source used to come back empty).
3. ``CustomMenu/**/*.command`` - user-made custom menu entries.
4. ``CustomTools/*.txt`` - tool presets.
5. Scripts under ``UserPrefs/Scripts``.

``English.xml`` supplies readable names for ids (also parsed leniently - it has
the same escaping bug), so the editor can show "New — CLEARSCENE".

Everything is read-only: nothing here writes to 3DCoat's files.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .log import log  # noqa: F401  (kept for callers that log catalog failures)


@dataclass
class CommandEntry:
    """One catalog entry."""

    cid: str          # identifier handed to coat.ui.cmd() ("$" prefix added at run time)
    label: str = ""   # readable name (translation when we have one)
    room: str = ""    # "" = global
    source: str = ""  # menu | hotkeys | custommenu | tool | script
    hint: str = ""    # menu/submenu or group the entry was found in

    @property
    def cmd_string(self) -> str:
        return self.cid if self.cid.startswith("$") else "$" + self.cid


# ---------------------------------------------------------------------------
# locations
# ---------------------------------------------------------------------------


def _documents() -> str:
    try:
        import coat  # type: ignore
        return str(coat.io.documents())
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Documents")


def install_root() -> str:
    """3DCoat's program folder (holds the authoritative menu definitions)."""
    try:
        import coat  # type: ignore
        root = str(coat.io.installPath())
        if root:
            return root
    except Exception:
        pass
    try:
        marker = os.path.join(_documents(), "3DCoat", "executable.txt")
        with open(marker, encoding="utf-8", errors="replace") as fh:
            exe = fh.read().strip().splitlines()[0].strip()
        if exe:
            return os.path.dirname(exe)
    except Exception:
        pass
    return ""


def hotkeys_path() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "Preferences", "Options_Hotkeys.xml")


def custom_menu_root() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "CustomMenu")


def custom_tools_root() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "CustomTools")


def scripts_root() -> str:
    return os.path.join(_documents(), "3DCoat", "UserPrefs", "Scripts")


def std_scripts_root() -> str:
    root = install_root()
    return os.path.join(root, "UserPrefs", "StdScripts") if root else ""


def c_templates_root() -> str:
    root = std_scripts_root()
    return os.path.join(root, "cTemplates") if root else ""


def english_xml_path() -> str:
    root = install_root()
    return os.path.join(root, "data", "Languages", "English.xml") if root else ""


# ---------------------------------------------------------------------------
# lenient parsing (3DCoat writes un-escaped '&' into its own XML)
# ---------------------------------------------------------------------------

_HOTKEY_BLOCK = re.compile(r"<OneHotKey>(.*?)</OneHotKey>", re.S)
_MENU_ITEM = re.compile(r'menu_item\(\s*"([^"\n]+)"\s*\)')
_TEXT_ITEM = re.compile(r"<TextItem>(.*?)</TextItem>", re.S)


def _tag(block: str, name: str) -> str:
    match = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return match.group(1).strip() if match else ""


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------


def read_menu_commands(root: str | None = None) -> list[CommandEntry]:
    """Every ``menu_item("<id>")`` in 3DCoat's own menu and tool definitions."""
    root = root if root is not None else c_templates_root()
    out: dict[str, CommandEntry] = {}
    if not root or not os.path.isdir(root):
        return []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            group = os.path.splitext(name)[0]
            parent = os.path.basename(dirpath)
            if parent and parent != os.path.basename(root):
                group = f"{parent}/{group}"
            for line in _read_text(os.path.join(dirpath, name)).splitlines():
                code = line.split("#", 1)[0]  # ignore commented-out calls
                for match in _MENU_ITEM.finditer(code):
                    # Some definitions write menu_item("$ID"); normalise it away,
                    # otherwise the id neither sorts nor looks up its name.
                    cid = match.group(1).strip().lstrip("$")
                    if not cid or cid in out:
                        continue
                    out[cid] = CommandEntry(cid=cid, label=cid, source="menu", hint=group)
    return sorted(out.values(), key=lambda e: (e.hint, e.cid))


def iter_hotkey_blocks(path: str | None = None) -> list[dict]:
    """All hotkey bindings, parsed leniently (no XML parser - see module docstring).

    Each item: id, room, code, ctrl, alt, shift. Used by the catalog *and* by
    ``core.hotkeys`` so there is one place that knows how to survive 3DCoat's
    broken escaping.
    """
    text = _read_text(path or hotkeys_path())
    out: list[dict] = []
    if not text:
        return out
    for block in _HOTKEY_BLOCK.findall(text):
        cid = _tag(block, "ID")
        if not cid:
            continue
        out.append(
            {
                "id": cid,
                "room": _tag(block, "Room"),
                "code": _tag(block, "Code"),
                "ctrl": _tag(block, "Ctrl").lower() == "true",
                "alt": _tag(block, "Alt").lower() == "true",
                "shift": _tag(block, "Shift").lower() == "true",
            }
        )
    return out


def read_hotkey_commands(path: str | None = None) -> list[CommandEntry]:
    """Ids from ``Options_Hotkeys.xml`` (room tagged), parsed leniently."""
    out: dict[str, CommandEntry] = {}
    for block in iter_hotkey_blocks(path):
        cid = block["id"]
        if cid in out:
            continue
        out[cid] = CommandEntry(cid=cid, label=cid, room=block["room"], source="hotkeys")
    return sorted(out.values(), key=lambda e: (e.room, e.cid))


def read_custom_menu_commands(root: str | None = None) -> list[CommandEntry]:
    """3DCoat's ``*.command`` files (display name / command id / tooltip)."""
    root = root or custom_menu_root()
    out: list[CommandEntry] = []
    if not os.path.isdir(root):
        return out
    for dirpath, _dirnames, filenames in os.walk(root):
        section = os.path.relpath(dirpath, root).replace("\\", "/")
        for name in filenames:
            if not name.lower().endswith(".command"):
                continue
            lines = [ln.strip() for ln in _read_text(os.path.join(dirpath, name)).splitlines()]
            label = lines[0] if lines else name
            cid = re.sub(r"^\$", "", lines[1]) if len(lines) > 1 and lines[1] else ""
            if not cid:
                continue
            out.append(CommandEntry(cid=cid, label=label or cid, room=section, source="custommenu"))
    return out


def read_tool_commands(root: str | None = None) -> list[CommandEntry]:
    """Tool presets (``CustomTools/<Name>.txt``) - each file name is a tool id."""
    root = root if root is not None else custom_tools_root()
    out: list[CommandEntry] = []
    if not root or not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if not name.lower().endswith(".txt"):
            continue
        cid = os.path.splitext(name)[0]
        out.append(CommandEntry(cid=cid, label=cid, source="tool", hint="tool"))
    return out


# --- 3DCoat's own tool panels -----------------------------------------------
_TOOLS_ITEM = re.compile(r'tools_item\(\s*"([^"\n]+)"\s*\)\s*(?:#\s*(.*))?')
_TOOLS_SECTION = re.compile(r'@d_tools_section\(\s*"([^"\n]+)"\s*\)')
_FAMILY_PREFIX = re.compile(r"^(\{[^}]*\}|\[[^]]*\])*")


def read_toolpanel_commands(root: str | None = None) -> list[CommandEntry]:
    """The tools on 3DCoat's own tool panels.

    ``sculptTools.py`` and friends call ``coat.tools_item("[extension]VoxLayer")``
    with 3DCoat's own readable name in the trailing comment, and
    ``@d_tools_section`` marks the panel section - so these entries arrive named
    and grouped the way the UI shows them. Authoritative and in the program
    folder, like the menu definitions.
    """
    root = root if root is not None else c_templates_root()
    out: list[CommandEntry] = []
    seen: set[str] = set()
    if not root or not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            room = os.path.splitext(name)[0]
            section = ""
            for line in _read_text(os.path.join(dirpath, name)).splitlines():
                if line.lstrip().startswith("#"):
                    continue  # a commented-out tools_item is not a tool
                found = _TOOLS_SECTION.search(line)
                if found:
                    section = found.group(1).strip()
                    continue
                match = _TOOLS_ITEM.search(line)
                if not match:
                    continue
                cid = match.group(1).strip()
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                label = (match.group(2) or "").strip() or cid
                out.append(CommandEntry(cid=cid, label=label, room=room,
                                        source="toolpanel", hint=section))
    return out


def tool_id_name(cid: str) -> str:
    """``{FLT}[extension]SCULP_PLANE`` -> ``SCULP_PLANE``.

    Tool ids carry modifier groups and a family tag (``[extension]``,
    ``[StdPen]``); the bare name is what a ``CustomTools`` preset file matches.
    """
    return _FAMILY_PREFIX.sub("", cid).strip()


def read_my_tools(root: str | None = None) -> list[CommandEntry]:
    """The tools that have a preset of the user's own (``CustomTools/*.txt``).

    3DCoat's equivalent of Krita's "Brushes" source: the presets you built, ready
    to drop into a menu. The payload is the tool id itself (``$[extension]Blob``),
    not the file name, because that is what actually switches the tool.
    """
    tools_root = root or custom_tools_root()
    if not tools_root or not os.path.isdir(tools_root):
        return []
    mine = sorted(os.path.splitext(n)[0] for n in os.listdir(tools_root)
                  if n.lower().endswith(".txt"))
    if not mine:
        return []
    wanted = set(mine)
    out: list[CommandEntry] = []
    matched: set[str] = set()
    for entry in read_toolpanel_commands():
        bare = tool_id_name(entry.cid)
        if bare in wanted:
            out.append(entry)
            matched.add(bare)
    out.sort(key=lambda e: (e.hint, e.label.lower()))
    # A preset with no panel entry still gets a row - it may be a tool this build
    # does not ship, and the family tag is the one 3DCoat uses for user presets.
    for bare in mine:
        if bare in matched:
            continue
        out.append(CommandEntry(cid=f"[extension]{bare}", label=bare,
                                source="toolpanel", hint="Other"))
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


def read_translations(path: str | None = None) -> dict[str, str]:
    """``id -> readable name`` from English.xml (lenient - same escaping bug)."""
    path = path if path is not None else english_xml_path()
    text = _read_text(path)
    out: dict[str, str] = {}
    if not text:
        return out
    for block in _TEXT_ITEM.findall(text):
        cid = _tag(block, "ID")
        name = _tag(block, "Text")
        if not cid or not name or cid in out:
            continue
        name = re.sub(r"<[^>]+>", "", name)
        name = " ".join(name.split())
        for entity, char in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                             ("&apos;", "'"), ("&amp;", "&")):
            name = name.replace(entity, char)
        if not name or len(name) > 60:
            continue
        out[cid] = name
    return out


def read_all_commands(translations: dict[str, str] | None = None) -> list[CommandEntry]:
    """The combined source the editor shows (menu + hotkeys + custom menu).

    Readable names come from the translation table, so entries read
    "New — CLEARSCENE" instead of bare ids.
    """
    merged: dict[str, CommandEntry] = {}
    for entry in read_menu_commands():
        merged[entry.cid] = entry
    for entry in read_hotkey_commands():
        existing = merged.get(entry.cid)
        if existing is None:
            merged[entry.cid] = entry
        elif not existing.room:
            existing.room = entry.room
    for entry in read_custom_menu_commands():
        existing = merged.get(entry.cid)
        if existing is None:
            merged[entry.cid] = entry
        else:
            existing.label = entry.label or existing.label

    names = translations if translations is not None else read_translations()
    rows: list[CommandEntry] = []
    for entry in merged.values():
        display = names.get(entry.cid) or (entry.label if entry.label != entry.cid else "")
        entry.label = display or entry.cid
        rows.append(entry)
    rows.sort(key=lambda e: (e.label.lower(), e.cid))
    return rows


def describe_counts() -> str:
    """One-line summary (used in logs)."""
    return (
        f"menu={len(read_menu_commands())} "
        f"hotkeys={len(read_hotkey_commands())} "
        f"custommenu={len(read_custom_menu_commands())} "
        f"tools={len(read_tool_commands())} "
        f"scripts={len(read_script_commands())} "
        f"names={len(read_translations())}"
    )
