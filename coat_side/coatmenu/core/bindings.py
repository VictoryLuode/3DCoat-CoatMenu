"""
CoatMenu - which key each list is bound to.

3DCoat owns the binding UI (Preferences > Hotkeys) and CoatMenu never writes that
file - it is far too easy to corrupt. What we *can* do is read it back and report
what we see, which is how "this list has no key" or "two lists fight over one
key" gets noticed before it turns into a mystery.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from coatmenu.core import menus_registry
from coatmenu.core.config import MenuConfig
from coatmenu.core.hotkeys import code_to_vk, read_bindings

# Names for the codes 3DCoat writes that are not a single character.
_PRETTY = {
    "BACK": "Backspace",
    "TAB": "Tab",
    "ENTER": "Enter",
    "ESC": "Esc",
    "SPACE": "Space",
    "INS": "Insert",
    "DELETE": "Delete",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
    "HOME": "Home",
    "END": "End",
    "PGUP": "PageUp",
    "PGDN": "PageDown",
}


def key_label(code: str) -> str:
    """Human name for one ``<Code>`` value ("" when it is unbound)."""
    raw = (code or "").strip()
    upper = raw.upper()
    if not raw or upper in ("KEY_00", "KEY_"):
        return ""
    if upper in _PRETTY:
        return _PRETTY[upper]
    return upper


@dataclass
class Bindings:
    """What 3DCoat currently has bound to our menu ids."""

    keys: dict[str, str] = field(default_factory=dict)   # list name -> "Ctrl+Q"
    conflicts: list[str] = field(default_factory=list)   # human-readable notes

    def for_menu(self, name: str) -> str:
        return self.keys.get(name, "")


def describe(config: MenuConfig, path: str | None = None) -> Bindings:
    """Read the hotkey file once, then work out both the keys and the clashes."""
    wanted = {menu_id: lst.name for menu_id, lst in menus_registry.menu_ids(config)}
    by_combo: dict[tuple, list[str]] = defaultdict(list)
    keys: dict[str, str] = {}

    for entry in read_bindings(path):
        name = wanted.get(str(entry.get("id") or ""))
        if name is None:
            continue
        label = key_label(str(entry.get("code") or ""))
        if not label:
            continue
        modifiers = [
            pretty
            for field_name, pretty in (("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"))
            if entry.get(field_name)
        ]
        keys[name] = "+".join(modifiers + [label])

        vk = code_to_vk(str(entry.get("code") or ""))
        if vk:
            signature = (vk, bool(entry.get("ctrl")), bool(entry.get("alt")),
                         bool(entry.get("shift")))
            if name not in by_combo[signature]:
                by_combo[signature].append(name)

    conflicts = [
        f"{' and '.join(names)} are bound to the same key"
        for names in by_combo.values()
        if len(names) > 1
    ]
    return Bindings(keys=keys, conflicts=conflicts)
