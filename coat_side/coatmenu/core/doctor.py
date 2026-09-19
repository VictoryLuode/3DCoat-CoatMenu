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

from coatmenu.core import bindings as bindings_mod
from coatmenu.core import catalog, lists, paths
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


def report(config=None) -> str:
    """The whole picture, as plain text."""
    cfg = config if config is not None else lists.get_config()
    binds = bindings_mod.describe(cfg)
    startup = startup_path()

    out: list[str] = [
        "CoatMenu doctor",
        f"  time          : {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"  extension     : {paths.extension_root()}",
        f"  data          : {paths.data_dir()}",
        f"  lists.json    : {'ok' if os.path.exists(paths.config_path()) else 'MISSING'}",
        f"  startup.txt   : {'CoatMenu listed' if _startup_lists_us(startup) else 'CoatMenu NOT listed'}"
        f"  ({startup})",
        f"  command source: {catalog.describe_counts()}",
        f"  lists         : {len(cfg.lists)}",
    ]
    for lst in cfg.lists:
        out.append(
            f"    - {lst.name}  mode={lst.mode}  rows={len(lst.items)}"
            f"  key={binds.for_list(lst.name) or 'unbound'}"
        )
    out.append(f"  hotkey clashes: {'; '.join(binds.conflicts) or 'none'}")

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
