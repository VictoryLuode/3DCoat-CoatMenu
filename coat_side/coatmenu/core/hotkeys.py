"""
CoatMenu - hotkey lookup.

3DCoat stores every binding in ``UserPrefs/Preferences/Options_Hotkeys.xml``.
We only ever **read** it. The whole point of reading it is the "hold to open,
release to run" interaction: when the overlay opens we need to know which
physical key the user is currently holding so we can watch for the release.

Two ids can exist for the same script:

* the menu id we register (``CoatMenu_Show``)
* ``execute:<absolute script path>`` - created when the user binds the script
  from 3DCoat's Scripts browser

They are usually bound to the same key but not guaranteed, so we prefer the
candidate whose key is *currently held*.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from coatmenu.core.log import log

_NAMED_VK = {
    "BACK": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "INS": 0x2D,
    "DELETE": 0x2E,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "HOME": 0x24,
    "END": 0x23,
    "PGUP": 0x21,
    "PGDN": 0x22,
    "NUM*": 0x6A,
    "NUM/": 0x6F,
    "NUM_MINUS": 0x6D,
    "NUM_PLUS": 0x6B,
    "NUM.": 0x6E,
}


def code_to_vk(code: str) -> int:
    """Map a 3DCoat hotkey ``<Code>`` value to a Win32 virtual key.

    Returns 0 when the code is unbound (``key_00``) or unrecognised.
    """
    if not code:
        return 0
    raw = code.strip()
    upper = raw.upper()
    if upper.startswith("KEY_"):
        tail = upper[4:]
        if tail == "00":
            return 0  # 3DCoat's "unbound" placeholder
        try:
            return int(tail, 16)
        except ValueError:
            return 0
    if upper in _NAMED_VK:
        return _NAMED_VK[upper]
    if len(upper) == 2 and upper.startswith("F") and upper[1].isdigit():
        return 0x70 + int(upper[1]) - 1
    if len(upper) == 3 and upper.startswith("F") and upper[1:].isdigit():
        return 0x70 + int(upper[1:]) - 1
    if upper.startswith("NUM") and upper[3:].isdigit():
        return 0x60 + int(upper[3:])
    if len(raw) == 1:
        return ord(raw.upper())
    return 0


def _normalise_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(path.replace("/", os.sep)))


def read_bindings(path: str | None = None) -> list[dict]:
    """All bindings, as dicts: id, room, code, ctrl, alt, shift.

    Delegates to the catalog's lenient reader: 3DCoat writes un-escaped ``&``
    characters into this file, so a strict XML parser would throw the whole
    document away (which for us means losing every trigger-key lookup).
    """
    from coatmenu.core.catalog import iter_hotkey_blocks

    try:
        return iter_hotkey_blocks(path)
    except Exception as exc:
        log(f"hotkeys: cannot read {path or 'hotkeys file'}: {exc}")
        return []


def find_trigger_vk(candidates: list[str], path: str | None = None) -> int:
    """Virtual key currently used to launch us, or 0 if we cannot tell.

    ``candidates``: hotkey ids to match, plus optionally ``execute:<script>``.
    Preference order: bound *and currently held* > bound > nothing.
    """
    wanted_ids = {c for c in candidates if c and not c.lower().startswith("execute:")}
    wanted_paths = {
        _normalise_path(c.split(":", 1)[1])
        for c in candidates
        if c and c.lower().startswith("execute:") and len(c.split(":", 1)) > 1
    }

    bound: list[int] = []
    for entry in read_bindings(path):
        cid = entry["id"]
        matched = cid in wanted_ids
        if not matched and wanted_paths and cid.lower().startswith("execute:"):
            matched = _normalise_path(cid.split(":", 1)[1]) in wanted_paths
        if not matched:
            continue
        vk = code_to_vk(entry["code"])
        if vk:
            bound.append(vk)

    if not bound:
        return 0

    from coatmenu.ui.popup import is_key_down

    for vk in bound:
        if is_key_down(vk):
            return vk
    return bound[0]
