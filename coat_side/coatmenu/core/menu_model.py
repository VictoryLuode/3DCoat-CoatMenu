"""
CoatMenu - the menu item model.

Deliberately Qt-free: the installer, the config layer and the tests all build
menus without importing PySide6.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# kinds
COMMAND = "command"      # 3DCoat command id -> coat.ui.cmd("$id")
SCRIPT = "script"        # python file -> coat.io.executeScript(path)
PRESET = "preset"        # 3DCoat tool preset -> AppOptions.ActivateToolPreset(name)
SUBMENU = "submenu"      # opens a child panel
SEPARATOR = "separator"
HEADER = "header"        # dim group label
TITLE = "title"          # list title row


LIST = "list"
PIE = "pie"

# How a branch row unfolds. ``auto`` is the built-in behaviour (a pie shows up to
# PIE_INLINE_MAX children in the slot, more than that opens a panel on dwell); the
# others pin it either way.
EXPAND_AUTO = "auto"
EXPAND_INLINE = "inline"
EXPAND_PANEL = "panel"
EXPAND_MODES = (EXPAND_AUTO, EXPAND_INLINE, EXPAND_PANEL)

EXPAND_LABELS = {
    EXPAND_AUTO: "Auto",
    EXPAND_INLINE: "Inline",
    EXPAND_PANEL: "Panel",
}

# Where a pie slot sits. ``auto`` spreads the slots evenly with the first one
# straight up; the rest pin a row to a compass point so your hand can learn it
# (Freeze always up, Smooth always down).
POSITION_AUTO = "auto"
POSITION_TOP = "top"
POSITION_TOP_RIGHT = "top-right"
POSITION_RIGHT = "right"
POSITION_BOTTOM_RIGHT = "bottom-right"
POSITION_BOTTOM = "bottom"
POSITION_BOTTOM_LEFT = "bottom-left"
POSITION_LEFT = "left"
POSITION_TOP_LEFT = "top-left"

POSITION_MODES = (
    POSITION_AUTO,
    POSITION_TOP, POSITION_TOP_RIGHT, POSITION_RIGHT, POSITION_BOTTOM_RIGHT,
    POSITION_BOTTOM, POSITION_BOTTOM_LEFT, POSITION_LEFT, POSITION_TOP_LEFT,
)

POSITION_LABELS = {
    POSITION_AUTO: "Auto",
    POSITION_TOP: "Top",
    POSITION_TOP_RIGHT: "Top right",
    POSITION_RIGHT: "Right",
    POSITION_BOTTOM_RIGHT: "Bottom right",
    POSITION_BOTTOM: "Bottom",
    POSITION_BOTTOM_LEFT: "Bottom left",
    POSITION_LEFT: "Left",
    POSITION_TOP_LEFT: "Top left",
}

# Degrees clockwise from straight up - the same convention ``_slot_angle`` uses.
POSITION_ANGLES = {
    POSITION_TOP: 0.0,
    POSITION_TOP_RIGHT: 45.0,
    POSITION_RIGHT: 90.0,
    POSITION_BOTTOM_RIGHT: 135.0,
    POSITION_BOTTOM: 180.0,
    POSITION_BOTTOM_LEFT: 225.0,
    POSITION_LEFT: 270.0,
    POSITION_TOP_LEFT: 315.0,
}


@dataclass
class MenuItem:
    """One row of a CoatMenu list."""

    label: str = ""
    kind: str = COMMAND
    cid: str = ""
    path: str = ""
    hint: str = ""
    enabled: bool = True
    children: list["MenuItem"] = field(default_factory=list)
    cmds: list[str] = field(default_factory=list)
    expand: str = EXPAND_AUTO
    position: str = POSITION_AUTO

    @property
    def clickable(self) -> bool:
        if not self.enabled or self.kind not in (COMMAND, SCRIPT, PRESET):
            return False
        return bool(self.cid or self.path or self.cmds)

    @property
    def is_branch(self) -> bool:
        return self.kind == SUBMENU or bool(self.children)

    @property
    def is_setting(self) -> bool:
        """Rows that open something rather than acting directly."""
        return self.kind in (SEPARATOR, HEADER, TITLE)


def separator() -> MenuItem:
    return MenuItem(kind=SEPARATOR)


def header(text: str) -> MenuItem:
    return MenuItem(label=text, kind=HEADER)


def title_item(text: str) -> MenuItem:
    """List title row (accent colour, underlined).

    Named ``_item`` because ``title`` is also a string argument elsewhere.
    """
    return MenuItem(label=text, kind=TITLE)


def submenu(label: str, children: list[MenuItem]) -> MenuItem:
    return MenuItem(label=label, kind=SUBMENU, children=list(children))


def sequence(label: str, cmds: list[str], cid: str = "") -> MenuItem:
    """One row that fires several commands in order.

    3DCoat has multi-step actions that are not a single command id (adding a
    primitive is "neutralise the tool, open the primitive tool, pick the shape").
    """
    return MenuItem(label=label, kind=COMMAND, cid=cid or (cmds[0] if cmds else ""),
                    cmds=[c for c in cmds if c])


def flatten(rows: list[MenuItem]) -> list[MenuItem]:
    """Every row in the tree, parents before children."""
    out: list[MenuItem] = []
    for row in rows:
        out.append(row)
        if row.children:
            out.extend(flatten(row.children))
    return out
