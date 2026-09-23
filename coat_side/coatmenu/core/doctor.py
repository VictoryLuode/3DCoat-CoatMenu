"""
CoatMenu - one-shot status report ("doctor").

Everything that decides whether CoatMenu works sits either in the user folder or
in 3DCoat's own files, so when something looks wrong the fastest path is to dump
all of it in one place: the lists, their bindings and clashes, how big the command
catalog is, whether the extension is listed in ``startup.txt``, and the tail of
our log. It is the first thing to read before guessing.
"""
from __future__ import annotations

import os
import time

from coatmenu import __version__
from coatmenu.core import bindings as bindings_mod
from coatmenu.core import catalog, menus, paths
from coatmenu.core.config import config_readable, unreadable_copies
from coatmenu.core.log import log, log_path

REPORT_NAME = "doctor.txt"
STARTUP_NAME = "startup.txt"
LOG_TAIL_LINES = 30


def startup_path() -> str:
    return os.path.join(paths.scripts_dir(), "cExtensions", STARTUP_NAME)


def _tail(path: str, count: int) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return [line.rstrip("\n") for line in fh.readlines()[-count:]]
    except OSError:
        return []


def _startup_lists_us(path: str) -> bool:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return any(line.strip() == "CoatMenu" for line in fh)
    except OSError:
        return False


PROBE_LIMIT = 2


def tool_probe(limit: int = PROBE_LIMIT) -> list[str]:
    """Do the tool commands really switch tools? Ask 3DCoat itself.

    ``CMD.GetCurrentToolID()`` is the one honest answer to that question, so the
    doctor switches a couple of the user's tools, reads the active id back, and
    puts the tool they started on back. Nothing else about the scene is touched.
    """
    try:
        import coat  # type: ignore
    except Exception as exc:  # pragma: no cover - only outside 3DCoat
        return [f"  tool probe    : no coat module ({exc})"]
    try:
        active = str(coat.GetCurrentToolID())
    except Exception as exc:  # pragma: no cover
        return [f"  tool probe    : GetCurrentToolID failed ({exc})"]

    lines = [f"  active tool   : {active}"]
    probes = [entry.cid for entry in catalog.read_my_tools()][:limit]
    for cid in probes:
        cmd = cid if cid.startswith("$") else "$" + cid
        try:
            coat.ui.cmd(cmd)
            now = str(coat.GetCurrentToolID())
        except Exception as exc:
            lines.append(f"    {cmd}  ->  error: {exc}")
            continue
        verdict = "" if now != active else "   (no change)"
        lines.append(f"    {cmd}  ->  {now}{verdict}")
    if probes:
        cmd = active if active.startswith("$") else "$" + active
        try:
            coat.ui.cmd(cmd)
            lines.append(f"    restored      ->  {coat.GetCurrentToolID()}")
        except Exception as exc:
            lines.append(f"    restore failed: {exc}")
    return lines


def config_line() -> str:
    """One line about the config file: present, readable, anything kept aside.

    A config that cannot be parsed is the one thing that makes "my menus are gone"
    look true, so the doctor says it outright instead of reporting "ok".
    """
    path = paths.config_path()
    if not os.path.exists(path):
        return "MISSING (a starter is written on the next start)"
    copies = unreadable_copies(path)
    if not config_readable(path):
        return f"UNREADABLE - left as it is ({path})"
    if copies:
        return f"ok, but {len(copies)} unreadable copy kept: {os.path.basename(copies[-1])}"
    return "ok"


def report(config=None) -> str:
    """The whole picture, as plain text."""
    cfg = config if config is not None else menus.get_config()
    binds = bindings_mod.describe(cfg)
    startup = startup_path()

    out: list[str] = [
        "CoatMenu doctor",
        f"  version       : {__version__}",
        f"  time          : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"  extension     : {paths.extension_root()}",
        f"  data          : {paths.data_dir()}",
        f"  menus.json    : {config_line()}",
        f"  startup.txt   : {'CoatMenu listed' if _startup_lists_us(startup) else 'CoatMenu NOT listed'}"
        f"  ({startup})",
        f"  command source: {catalog.describe_counts()}",
        f"  menus         : {len(cfg.menus)}",
    ]
    if cfg.removed_presets:
        # Built-in lists he deleted on purpose: an install will not add these back,
        # and "+ New ▸ Built-in lists" in the editor is how they come back.
        out.append(f"  deleted built-ins: {', '.join(cfg.removed_presets)} "
                   f"(not re-added by an install)")
    for lst in cfg.menus:
        out.append(
            f"    - {lst.name}  mode={lst.mode}  rows={len(lst.items)}"
            f"  key={binds.for_menu(lst.name) or 'unbound'}"
        )
    out.append(f"  hotkey clashes: {'; '.join(binds.conflicts) or 'none'}")
    out.append("  keys          : bind them in 3DCoat - hover the entry in "
               "Scripts > CoatMenu and press END")
    # Leftovers from the old insertInMenu path would list every menu twice.
    items_dir = os.path.join(paths.scripts_dir(), "ExtraMenuItems")
    try:
        leftovers = sorted(
            name for name in os.listdir(items_dir)
            if name.startswith("CoatMenu_") and name.endswith(".xml")
        )
        out.append(f"  extra items   : {', '.join(leftovers) if leftovers else 'none'}")
    except OSError:
        out.append("  extra items   : (folder missing)")
    out.extend(tool_probe())

    path = log_path()
    out.append(f"  log           : {path}")
    out.extend(f"    | {line}" for line in _tail(path, LOG_TAIL_LINES))
    return "\n".join(out)


def run(config=None) -> str:
    """Write the report next to the user's data, and return it."""
    text = report(config)
    target = os.path.join(paths.data_dir(), REPORT_NAME)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
        log(f"doctor: report written to {target}")
    except OSError as exc:
        log(f"doctor: cannot write {target}: {exc}")
    return text
