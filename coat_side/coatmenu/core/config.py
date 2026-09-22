"""
CoatMenu - list configuration.

The JSON shape is deliberately the same one Krita MenuBelt uses, so a list can
be moved between the two add-ons:

```json
{
  "version": 1,
  "menus": [
    {
      "name": "Sculpt",
      "items": [
        "Resample",
        { "id": "VIEW_WIREFRAME", "label": "Wireframe" },
        { "script": "C:/.../speedup.py", "label": "Speed up" },
        { "name": "Booleans", "items": ["SubtractVolume"] },
        { "header": "Shading" },
        { "separator": true }
      ]
    }
  ]
}
```

Item forms (identical to MenuBelt): a bare string is a command id; a dict with
``id`` is a command with optional renamed label; ``script`` is a python file;
``name`` + ``items`` is a submenu; ``separator``/``header`` are decoration.

Missing file -> a starter config holding the lists we ship, each one built against
the 3DCoat that is running so a first run already has entries that work.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import zlib
from dataclasses import dataclass, field

from coatmenu.core.menu_model import (
    EXPAND_AUTO,
    EXPAND_MODES,
    POSITION_AUTO,
    POSITION_MODES,
    MenuItem,
    header as header_item,
    separator as separator_item,
    submenu as submenu_item,
)

CONFIG_VERSION = 1
MAX_LISTS = 40
MAX_ITEMS_PER_LIST = 200


def slugify(name: str) -> str:
    """ASCII slug used for hotkey ids and generated entry scripts.

    A pure function of the name, so a list keeps its slug - and the hotkey bound
    to it - from one session to the next.

    A name that is not ASCII cannot be carried by the slug on its own. Every such
    name used to come back as ``menu``, which meant two Chinese (or Japanese, or
    Russian) lists shared one launcher file and one hotkey id, and the second one
    was unreachable. Those get a short hash of the name appended instead, so two
    different names only collide if the hashes do. ASCII names are untouched -
    the same slugs as before, so existing bindings and script names do not move.
    """
    original = str(name or "")
    text = unicodedata.normalize("NFKD", original).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    if any(ord(char) > 127 for char in original):
        digest = f"{zlib.crc32(original.encode('utf-8')) % 0x10000:04x}"
        return f"{text}_{digest}" if text else f"menu_{digest}"
    return text or "menu"


@dataclass
class Menu:
    """One menu - a named set of rows.

    ``mode`` is how it opens: ``list`` (rows) or ``pie`` (radial).
    """

    name: str
    items: list[MenuItem] = field(default_factory=list)
    mode: str = "list"
    preset: str = ""  # marker ("prims/2") for lists we ship and may refresh

    @property
    def slug(self) -> str:
        return slugify(self.name)

    @property
    def hotkey_id(self) -> str:
        """Id registered in 3DCoat's menu (bindable in Preferences > Hotkeys)."""
        return f"CoatMenu_{self.slug}"


def item_from_json(raw) -> MenuItem | None:
    """Build a :class:`MenuItem` from one JSON entry (never raises)."""
    item = _item_body_from_json(raw)
    if item is not None and isinstance(raw, dict):
        mode = str(raw.get("expand") or "").strip().lower()
        if mode in EXPAND_MODES:
            item.expand = mode
        spot = str(raw.get("position") or raw.get("where") or "").strip().lower()
        if spot in POSITION_MODES:
            item.position = spot
    return item


def _item_body_from_json(raw) -> MenuItem | None:
    if isinstance(raw, str):
        return MenuItem(label=raw, kind="command", cid=raw) if raw else None

    if not isinstance(raw, dict):
        return None

    if raw.get("separator"):
        return separator_item()

    if "header" in raw:
        text = str(raw.get("header") or "").strip()
        return header_item(text) if text else None

    if "name" in raw:
        children = [i for i in (item_from_json(c) for c in raw.get("items") or []) if i]
        label = str(raw.get("name") or "").strip()
        if not label:
            return None
        return submenu_item(label, children)

    if "preset" in raw:
        # Tool presets are no longer supported: the documented activation API does
        # not exist on this build, so a preset row could never work. Skip it rather
        # than let the loader turn it into a $command that cannot resolve.
        return None

    if "script" in raw:
        path = str(raw.get("script") or "").strip()
        if not path:
            return None
        label = str(raw.get("label") or os.path.basename(path) or path).strip()
        return MenuItem(label=label, kind="script", path=path, cid=path)

    if "cmds" in raw:
        # Multi-step action: a list of command ids fired in order.
        cmds = [str(c).strip() for c in raw.get("cmds") or [] if str(c).strip()]
        if not cmds:
            return None
        label = str(raw.get("label") or cmds[-1]).strip()
        return MenuItem(label=label, kind="command", cid=cmds[0], cmds=cmds)

    if "id" in raw:
        cid = str(raw.get("id") or "").strip()
        if not cid:
            return None
        return MenuItem(label=str(raw.get("label") or cid).strip(), kind="command", cid=cid)

    return None


def item_to_json(item: MenuItem):
    """Serialise one entry back to the compact shared form."""
    body = _item_body(item)
    # Only mention how it unfolds / where it sits when that is not the default -
    # the config stays as short as it was.
    if isinstance(body, dict) and (item.expand != EXPAND_AUTO or item.position != POSITION_AUTO):
        body = dict(body)
        if item.expand != EXPAND_AUTO:
            body["expand"] = item.expand
        if item.position != POSITION_AUTO:
            body["position"] = item.position
    return body


def _item_body(item: MenuItem):
    """The entry's own shape, without the global key."""
    if item.kind == "separator":
        return {"separator": True}
    if item.kind == "header":
        return {"header": item.label}
    if item.kind in ("submenu",) or item.children:
        return {"name": item.label, "items": [item_to_json(c) for c in item.children]}
    if item.kind == "script":
        return {"script": item.path or item.cid, "label": item.label}
    if item.kind == "preset":
        return {"preset": item.cid, "label": item.label}
    if item.cmds:
        return {"cmds": list(item.cmds), "label": item.label}
    cid = item.cid or item.label
    if item.label and item.label != cid:
        return {"id": cid, "label": item.label}
    return cid


def _clean_items(items: list[MenuItem], depth: int = 0) -> list[MenuItem]:
    out: list[MenuItem] = []
    for item in items:
        if depth < 4 and item.children:
            item.children = _clean_items(item.children, depth + 1)
        out.append(item)
        if len(out) >= MAX_ITEMS_PER_LIST:
            break
    return out


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@dataclass
class MenuConfig:
    """The whole user configuration."""

    menus: list[Menu] = field(default_factory=list)

    # -- lookup ----------------------------------------------------------

    def find(self, key: str) -> Menu | None:
        """Find a menu by slug, hotkey id, or name (case-insensitive)."""
        if not key:
            return None
        wanted = str(key).strip().lower()
        for lst in self.menus:
            if wanted in (lst.slug.lower(), lst.hotkey_id.lower(), lst.name.lower()):
                return lst
        return None

    def unique_name(self, base: str) -> str:
        """A menu name not yet used (appends 2, 3, ...)."""
        existing = {lst.name.lower() for lst in self.menus}
        if base.lower() not in existing:
            return base
        index = 2
        while f"{base} {index}".lower() in existing:
            index += 1
        return f"{base} {index}"

    # -- io --------------------------------------------------------------

    @classmethod
    def from_json(cls, data) -> "MenuConfig":
        menus: list[Menu] = []
        if isinstance(data, dict):
            # "menus" is the current key; "lists" is what the file used before the
            # terminology pass and is still read so an existing file keeps working.
            raw_menus = data.get("menus") or data.get("lists") or []
        elif isinstance(data, list):  # tolerate a bare list of menus
            raw_menus = data
        else:
            raw_menus = []
        for raw in raw_menus:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            items = _clean_items([i for i in (item_from_json(r) for r in raw.get("items") or []) if i])
            menus.append(Menu(name=name, items=items, mode=str(raw.get("mode") or "list"),
                              preset=str(raw.get("preset") or "")))
            if len(menus) >= MAX_LISTS:
                break
        return cls(menus=menus)

    def to_json(self) -> dict:
        out: list[dict] = []
        for lst in self.menus:
            data = {
                "name": lst.name,
                "mode": lst.mode,
                "items": [item_to_json(i) for i in lst.items],
            }
            if lst.preset:
                # Only shipped presets carry this; it lets the installer refresh
                # them without ever touching a menu of the same name built by hand.
                data["preset"] = lst.preset
            out.append(data)
        return {
            "version": CONFIG_VERSION,
            "menus": out,
        }

    @classmethod
    def load(cls, path: str) -> "MenuConfig":
        """Read the config; a missing or broken file falls back to the starter."""
        try:
            with open(path, encoding="utf-8") as fh:
                return cls.from_json(json.load(fh))
        except FileNotFoundError:
            return starter_config()
        except Exception:
            return starter_config()

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.to_json(), fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    # -- editing helpers (used by the editor and the tests) ---------------

    def add_menu(self, name: str) -> Menu:
        lst = Menu(name=self.unique_name(name or "New menu"))
        self.menus.append(lst)
        return lst

    def remove_menu(self, name: str) -> bool:
        target = self.find(name)
        if target is None or len(self.menus) <= 1:
            return False
        self.menus.remove(target)
        return True

    def set_mode(self, key: str, mode: str) -> bool:
        """Pick how a list renders: ``list`` (rows) or ``pie`` (radial)."""
        target = self.find(key)
        if target is None:
            return False
        target.mode = "pie" if str(mode).lower() == "pie" else "list"
        return True

    def rename_menu(self, old: str, new: str) -> Menu | None:
        target = self.find(old)
        new_name = (new or "").strip()
        if target is None or not new_name:
            return None
        if new_name != target.name:
            target.name = self.unique_name(new_name)
        return target

    def move_menu(self, name: str, delta: int) -> bool:
        target = self.find(name)
        if target is None:
            return False
        index = self.menus.index(target)
        new_index = max(0, min(len(self.menus) - 1, index + delta))
        if new_index == index:
            return False
        self.menus.insert(new_index, self.menus.pop(index))
        return True


# ---------------------------------------------------------------------------
# starter config
# ---------------------------------------------------------------------------


def starter_config(documents: str | None = None) -> MenuConfig:
    """First-run config: the lists we ship, built for this build of 3DCoat.

    Each list is built against the 3DCoat that is running (``presets.default_lists``),
    so a first run starts with rows that work rather than with an empty editor.

    When not one of them can find a command this build defines - no program folder
    to read, or a 3DCoat whose ids we do not know - the config says so instead of
    filling up with rows that would do nothing.

    *documents* is accepted for backwards compatibility: the lists no longer come
    from the user's ``CustomMenu`` folder.
    """
    from coatmenu.core import presets

    menus = presets.default_lists()
    if not any(item.kind == "command" for lst in menus for item in lst.items):
        menus = [
            Menu(
                name="Starter",
                items=[header_item("3DCoat's own commands were not found - open "
                                   "Scripts > CoatMenu > Diagnostics (doctor)")],
            )
        ]
    return MenuConfig(menus=menus)


# ---------------------------------------------------------------------------
# a config we cannot read
# ---------------------------------------------------------------------------

# Suffix for a config we could not parse and moved aside instead of replacing.
# The installer uses the same one, so both paths leave the same mark.
UNREADABLE_TAG = ".unreadable-"


def config_readable(path: str) -> bool:
    """True when the file is absent or parses as JSON (it does not mean "has menus")."""
    try:
        with open(path, encoding="utf-8") as fh:
            json.load(fh)
    except FileNotFoundError:
        return True
    except Exception:
        return False
    return True


def quarantine_unreadable(path: str, stamp: str | None = None) -> str:
    """Move a config we cannot parse aside; returns its new path ("" if none).

    Writing a starter over his file would be data loss on a file that is usually
    repairable by hand, so the panel does not take that route: the unreadable file
    is *renamed*, and the next save writes a fresh config at the canonical path.
    Renaming rather than copying keeps exactly one file in play and leaves the
    original bytes untouched for him to recover (see AGENTS.md).
    """
    if not os.path.isfile(path) or config_readable(path):
        return ""
    target = f"{path}{UNREADABLE_TAG}{stamp or time.strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(path, target)
    except OSError:
        return ""
    return target


def unreadable_copies(config_path: str) -> list[str]:
    """Configs moved aside next to ``config_path`` (oldest first) - for the doctor."""
    folder, name = os.path.split(config_path)
    prefix = f"{name}{UNREADABLE_TAG}"
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return sorted(os.path.join(folder, n) for n in names if n.startswith(prefix))
