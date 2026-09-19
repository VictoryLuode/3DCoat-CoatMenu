"""
CoatMenu - menu data.

Demo stage: the list is built from 3DCoat's own ``CustomMenu/*.command`` files,
because those entries are guaranteed to be real commands that 3DCoat itself
generated and that the user has used before - clicking one and *seeing something
happen* is the whole point of a demo.

Next stage: this module loads ``data/lists.json`` (multi-list, user authored).
"""
from __future__ import annotations

from core import catalog
from ui.popup import MenuItem, header, separator

DEMO_SECTIONS = ("VoxelsCustom", "ModelingCustom")
MAX_PER_SECTION = 6


def demo_items() -> list[MenuItem]:
    """Small, real list for the first look."""
    entries = catalog.read_custom_menu_commands()
    items: list[MenuItem] = []
    used = 0
    for section in DEMO_SECTIONS:
        section_entries = [e for e in entries if e.room == section][:MAX_PER_SECTION]
        if not section_entries:
            continue
        items.append(header(section))
        for entry in section_entries:
            items.append(MenuItem(label=entry.label, kind="command", cid=entry.cid))
            used += 1
        items.append(separator())

    if not used:
        items = [
            header("CoatMenu (no CustomMenu entries found)"),
            MenuItem(label="Resample", kind="command", cid="Resample"),
            MenuItem(label="Smooth Object", kind="command", cid="SmoothObject"),
            separator(),
        ]

    return items


def stats_line() -> str:
    return catalog.describe_counts()
