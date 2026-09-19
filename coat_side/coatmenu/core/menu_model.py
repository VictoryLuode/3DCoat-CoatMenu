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
SUBMENU = "submenu"      # opens a child panel
SEPARATOR = "separator"
HEADER = "header"        # dim group label
TITLE = "title"          # list title row


LIST = "list"
PIE = "pie"


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

    @property
    def clickable(self) -> bool:
        if not self.enabled or self.kind not in (COMMAND, SCRIPT):
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
