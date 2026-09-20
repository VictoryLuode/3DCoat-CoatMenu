"""
CoatMenu - running one entry.

Deliberately outside the overlay: a generated shortcut script runs a row without
pulling Qt in, so clicking a row and pressing its global key go through exactly
the same code.
"""
from __future__ import annotations

from coatmenu.core.log import log
from coatmenu.core.menu_model import PRESET, SCRIPT, MenuItem


def run_item(item: MenuItem) -> None:
    """Execute one menu entry (never raises)."""
    try:
        import coat  # type: ignore
    except Exception as exc:
        log(f"run_item: coat import failed: {exc}")
        return
    try:
        if item.cmds:
            # Multi-step action: same frame, same order 3DCoat's own UI uses.
            for raw in item.cmds:
                cmd = raw if raw.startswith("$") else "$" + raw
                coat.ui.cmd(cmd)
            log(f"ran sequence: {item.cmds}")
        elif item.kind == SCRIPT:
            coat.io.executeScript(item.path or item.cid)
            log(f"ran script: {item.path or item.cid}")
        elif item.kind == PRESET:
            # A preset is a tool *and* its stored settings, so it goes through
            # 3DCoat's own preset API - the command bus cannot express it.
            coat.AppOptions.ActivateToolPreset(item.cid)
            log(f"activated preset: {item.cid}")
        else:
            cmd = item.cid if item.cid.startswith("$") else "$" + item.cid
            coat.ui.cmd(cmd)
            log(f"ran command: {cmd}")
    except Exception as exc:
        log(f"run_item failed ({item.kind} {item.cid}): {exc}", exc=True)
