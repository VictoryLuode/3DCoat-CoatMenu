"""Format Tools-tab button tooltips with Scripts-menu action names.

Action scripts register in 3DCoat as ``LKS: <filename>``. Including that
display name in panel button tooltips lets users find the matching item when
assigning hotkeys.
"""
from __future__ import annotations

from ported.utils.action_discovery import generate_display_name


def action_menu_tooltip(description: str, action_filename: str) -> str:
    """Build an HTML tooltip that includes the Scripts-menu item name.

    Args:
        description: Human-readable action description (may be empty).
        action_filename: Action script filename, e.g.
            ``SculptObject_Decimate_Half_Selected.py``.

    Returns:
        HTML tooltip with description plus a ``Menu: LKS: <filename>`` line.
    """
    menu_name: str = generate_display_name(action_filename)
    menu_line: str = (
        f"<span style='color:#90caf9;'>Menu:</span> <code>{menu_name}</code>"
    )
    desc: str = description.strip()
    if desc:
        return f"{desc}<br><br>{menu_line}"
    return menu_line
