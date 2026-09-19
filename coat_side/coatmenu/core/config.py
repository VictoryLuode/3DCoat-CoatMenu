"""
CoatMenu - list configuration.

The JSON shape is deliberately the same one Krita MenuBelt uses, so a list can
be moved between the two add-ons:

```json
{
  "version": 1,
  "lists": [
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

Missing file -> a starter config built from 3DCoat's own CustomMenu entries, so
the very first run already has entries that are guaranteed to work.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field

from coatmenu.core.menu_model import (
    MenuItem,
    header as header_item,
    separator as separator_item,
    submenu as submenu_item,
)

CONFIG_VERSION = 1
MAX_LISTS = 40
MAX_ITEMS_PER_LIST = 200


def slugify(name: str) -> str:
    """ASCII slug used for hotkey ids and generated entry scripts."""
    text = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "list"


@dataclass
class MenuList:
    """One named list of entries."""

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
        return f"CoatMenu_List_{self.slug}"


# ---------------------------------------------------------------------------
# item (de)serialisation
# ---------------------------------------------------------------------------


def item_from_json(raw) -> MenuItem | None:
    """Build a :class:`MenuItem` from one JSON entry (never raises)."""
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
    if item.kind == "separator":
        return {"separator": True}
    if item.kind == "header":
        return {"header": item.label}
    if item.kind in ("submenu",) or item.children:
        return {"name": item.label, "items": [item_to_json(c) for c in item.children]}
    if item.kind == "script":
        return {"script": item.path or item.cid, "label": item.label}
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

    lists: list[MenuList] = field(default_factory=list)

    # -- lookup ----------------------------------------------------------

    def find(self, key: str) -> MenuList | None:
        """Find a list by slug, hotkey id, or name (case-insensitive)."""
        if not key:
            return None
        wanted = str(key).strip().lower()
        for lst in self.lists:
            if wanted in (lst.slug.lower(), lst.hotkey_id.lower(), lst.name.lower()):
                return lst
        return None

    def unique_name(self, base: str) -> str:
        """A list name not yet used (appends 2, 3, ...)."""
        existing = {lst.name.lower() for lst in self.lists}
        if base.lower() not in existing:
            return base
        index = 2
        while f"{base} {index}".lower() in existing:
            index += 1
        return f"{base} {index}"

    # -- io --------------------------------------------------------------

    @classmethod
    def from_json(cls, data) -> "MenuConfig":
        lists: list[MenuList] = []
        if isinstance(data, dict):
            raw_lists = data.get("lists") or []
        elif isinstance(data, list):  # tolerate a bare list of lists
            raw_lists = data
        else:
            raw_lists = []
        for raw in raw_lists:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            items = _clean_items([i for i in (item_from_json(r) for r in raw.get("items") or []) if i])
            lists.append(MenuList(name=name, items=items, mode=str(raw.get("mode") or "list"),
                                  preset=str(raw.get("preset") or "")))
            if len(lists) >= MAX_LISTS:
                break
        return cls(lists=lists)

    def to_json(self) -> dict:
        out: list[dict] = []
        for lst in self.lists:
            data = {
                "name": lst.name,
                "mode": lst.mode,
                "items": [item_to_json(i) for i in lst.items],
            }
            if lst.preset:
                # Only shipped lists carry this; it lets the installer refresh
                # them without ever touching a hand-built list of the same name.
                data["preset"] = lst.preset
            out.append(data)
        return {
            "version": CONFIG_VERSION,
            "lists": out,
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

    def add_list(self, name: str) -> MenuList:
        lst = MenuList(name=self.unique_name(name or "New list"))
        self.lists.append(lst)
        return lst

    def remove_list(self, name: str) -> bool:
        target = self.find(name)
        if target is None or len(self.lists) <= 1:
            return False
        self.lists.remove(target)
        return True

    def set_mode(self, key: str, mode: str) -> bool:
        """Pick how a list renders: ``list`` (rows) or ``pie`` (radial)."""
        target = self.find(key)
        if target is None:
            return False
        target.mode = "pie" if str(mode).lower() == "pie" else "list"
        return True

    def rename_list(self, old: str, new: str) -> MenuList | None:
        target = self.find(old)
        new_name = (new or "").strip()
        if target is None or not new_name:
            return None
        if new_name != target.name:
            target.name = self.unique_name(new_name)
        return target

    def move_list(self, name: str, delta: int) -> bool:
        target = self.find(name)
        if target is None:
            return False
        index = self.lists.index(target)
        new_index = max(0, min(len(self.lists) - 1, index + delta))
        if new_index == index:
            return False
        self.lists.insert(new_index, self.lists.pop(index))
        return True


# ---------------------------------------------------------------------------
# starter config
# ---------------------------------------------------------------------------


def starter_config(documents: str | None = None) -> MenuConfig:
    """First-run config: real CustomMenu entries, so nothing is dead on arrival."""
    from coatmenu.core import catalog

    root = os.path.join(
        documents or os.path.join(os.path.expanduser("~"), "Documents"),
        "3DCoat",
        "UserPrefs",
        "CustomMenu",
    )
    entries = catalog.read_custom_menu_commands(root)
    sculpt = [e for e in entries if e.room == "VoxelsCustom"][:6]
    model = [e for e in entries if e.room == "ModelingCustom"][:6]

    def rows(source) -> list[MenuItem]:
        return [MenuItem(label=e.label, kind="command", cid=e.cid) for e in source]

    lists = [
        MenuList(name="Sculpt", items=rows(sculpt)),
        MenuList(name="Modeling", items=rows(model)),
    ]
    if not any(lst.items for lst in lists):
        lists = [
            MenuList(
                name="Starter",
                items=[
                    header_item("No CustomMenu entries found"),
                    MenuItem(label="Resample", kind="command", cid="Resample"),
                    MenuItem(label="Smooth Object", kind="command", cid="SmoothObject"),
                ],
            )
        ]
    return MenuConfig(lists=lists)
