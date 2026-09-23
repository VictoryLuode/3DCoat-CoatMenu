"""Compare the shipped lists with the live menus - run before every release.

    python tests/sync_defaults.py                  # report the differences
    python tests/sync_defaults.py --config <path>   # another menus.json
    python tests/sync_defaults.py --literal         # print a paste-ready block

Why this exists: what a first run gets is *the author's own working set*
(``presets.DEFAULT_LISTS``), so it drifts every time those menus change. Before a
release the shipped lists are re-synced from the copy the extension is actually
running, and that has to be a deliberate step rather than a memory.

Why it only reports and never writes: the live copy is not automatically right. A
row can use an id this build of 3DCoat does not define (which we drop by policy -
a shipped row must never do nothing), and a row can be *worse* than what we ship
(the live Shade pie had three view ids spelled without the underscores 3DCoat
uses). Writing whatever is live would quietly delete working rows, so differences
are listed for a human to decide on, and the paste-ready block marks what this
build cannot use.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "coat_side"))

from coatmenu.core import config as config_mod  # noqa: E402
from coatmenu.core import paths, presets  # noqa: E402


def live_config_path() -> str:
    """Where the running extension keeps its menus.

    Not ``paths.data_dir()``: from a git checkout that points at the checkout
    (which has no user data), while the menus that matter are in the *installed*
    copy under the 3DCoat user folder.
    """
    env = os.environ.get("COATMENU_CONFIG")
    if env:
        return env
    return os.path.join(paths.scripts_dir(), "cExtensions", "CoatMenu", "data",
                        "menus.json")


# --- rows ---------------------------------------------------------------------
def _extras(item) -> dict:
    """``expand``/``position`` - only when set, so a live row and a written one
    compare equal (both spell the default as "auto", which is left out)."""
    out = {}
    for name in ("expand", "position"):
        value = getattr(item, name, "") or ""
        if value and value != "auto":
            out[name] = value
    return out


def rows_of(items) -> list:
    """Rows as the literals presets.py is written in.

    A submenu keeps its rows in ``children``, not ``items``. A label equal to the
    id is left out too, so a live row and a written one come out identical.
    """
    out: list = []
    for item in items:
        if item.kind == "header":
            out.append({"header": item.label})
        elif item.kind == "separator":
            out.append({"separator": True})
        elif item.kind == "submenu":
            row = {"name": item.label}
            row.update(_extras(item))
            row["items"] = rows_of(item.children)
            out.append(row)
        else:
            row: dict = {"id": item.cid}
            if item.label != item.cid:
                row["label"] = item.label
            if item.cmds and list(item.cmds) != [item.cid]:
                row["cmds"] = list(item.cmds)
            row.update(_extras(item))
            out.append(row)
    return out


def groups(rows: list, path: str = "") -> dict[str, list]:
    """``path -> [rows]``, submenu rows as structure only.

    Comparing row lists *in place* matters: two menus can hold rows at the same
    spot, and keying by path alone would silently drop one of them.
    """
    out: dict[str, list] = {}
    for row in rows:
        if isinstance(row, dict) and "items" in row:
            structure = {key: value for key, value in row.items() if key != "items"}
            out.setdefault(path, []).append(structure)
            for key, value in groups(row["items"], path + row["name"] + " > ").items():
                out.setdefault(key, []).extend(value)
        else:
            out.setdefault(path, []).append(row)
    return out


def show(path: str) -> str:
    return path[:-3] if path.endswith(" > ") else (path or "(top level)")


def describe(row: dict, live: bool = False) -> str:
    if "header" in row:
        return f"header {row['header']!r}"
    if "separator" in row:
        return "separator"
    if "id" not in row:
        # A submenu, kept to its shape: its rows are compared on their own path.
        extra = "  ".join(f"{k}={row[k]}" for k in ("expand", "position") if k in row)
        return f"submenu {row.get('name', '?')!r}" + (f"   [{extra}]" if extra else "")
    text = f"{row.get('label', row['id'])!r} -> {row['id']}"
    if row.get("cmds"):
        text += f"  ({len(row['cmds'])} steps)"
    if live:
        unknown = unknown_steps(row)
        if unknown:
            text += f"   [not defined here: {', '.join(unknown)}]"
    return text


def unknown_steps(row: dict) -> list[str]:
    """Steps of a row this build does not define.

    The same judgement the builders make, so this cannot cry wolf on the rows we
    ship: a step written ``$Tool::param`` is a tool parameter (3DCoat defines it as
    the bare ``param``), which is how primitive rows are validated.
    """
    universe = presets._universe()
    if not universe:
        return []
    out = []
    for step in (row.get("cmds") or [row["id"]]):
        tail = str(step).lstrip("$").split("::")[-1]
        if not (presets._known(universe, step) or presets._known(universe, tail)):
            out.append(step)
    return out


def literal(rows: list, indent: int = 0) -> list[str]:
    """The rows as they would be written in presets.py."""
    pad = " " * (indent + 4)
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict) and "items" in row:
            head = f"{{\"name\": {json.dumps(row['name'], ensure_ascii=False)}, "
            for extra in ("expand", "position"):
                if extra in row:
                    head += f"\"{extra}\": \"{row[extra]}\", "
            out.append(f"{pad}{head}\"items\": [")
            out += literal(row["items"], indent + 4)
            out.append(f"{pad}]}},")
            continue
        note = ""
        unknown = unknown_steps(row)
        if unknown:
            note = f"  # not defined in this build: {', '.join(unknown)}"
        out.append(f"{pad}{json.dumps(row, ensure_ascii=False)}," + note)
    return out


# --- the report ---------------------------------------------------------------
def report(live, shipped: dict, show_literal: bool) -> int:
    differing = 0
    for name in presets.DEFAULT_LISTS:
        built = shipped[name]
        menu = live.find(name)
        print(f"=== {name}")
        if menu is None:
            print(f"    not in the live menus - nothing to sync from "
                  f"(shipped: {len(built.items)} rows)")
            differing += 1
            continue

        live_rows, built_rows = rows_of(menu.items), rows_of(built.items)
        live_groups, built_groups = groups(live_rows), groups(built_rows)

        print(f"    live {len(live_rows)} rows  /  shipped {len(built_rows)} rows"
              f"   mode: live={menu.mode} shipped={built.mode}")
        problems: list[str] = []
        for key in list(live_groups) + [k for k in built_groups
                                        if k not in live_groups]:
            shipped_rows = built_groups.get(key, [])
            if [json.dumps(r, sort_keys=True) for r in shipped_rows] == [
                    json.dumps(r, sort_keys=True) for r in live_groups.get(key, [])]:
                continue
            if key not in built_groups:
                problems.append(f"    + live has, we do not:  {show(key)}"
                                f"  ({len(live_groups[key])} rows)")
            elif key not in live_groups:
                problems.append(f"    - we ship, live does not:  {show(key)}"
                                f"  ({len(shipped_rows)} rows)")
            else:
                problems.append(f"    ~ {show(key)}:  shipped {len(shipped_rows)}"
                                f" rows, live {len(live_groups[key])} rows")
            # -shipped / +live, so a row spelled one way there and another here stands out.
            for line in difflib.unified_diff(
                    [describe(row) for row in shipped_rows],
                    [describe(row, live=True) for row in live_groups.get(key, [])],
                    lineterm="", n=0):
                if line.startswith(("---", "+++", "@@")):
                    continue
                problems.append(f"        {line[0]} {line[1:]}")
        if menu.mode != built.mode:
            problems.append(f"    ~ mode differs: live={menu.mode} shipped={built.mode}")

        if not problems:
            print("    in sync")
            continue
        differing += 1
        for line in problems:
            print(line)
        if show_literal:
            var = name.upper().replace(" ", "_") + "_MENU_ROWS"
            print("    from the live menus, written the way presets.py writes them:")
            print(f"{var}: list = [")
            for line in literal(live_rows):
                print(line)
            print("]")
        print()
    return differing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="menus.json to compare against "
                                         "(default: the installed extension's)")
    parser.add_argument("--literal", action="store_true",
                        help="print a paste-ready block for each list that differs")
    args = parser.parse_args()

    path = args.config or live_config_path()
    if not os.path.isfile(path):
        print(f"!! no such file: {path}")
        return 2
    live = config_mod.MenuConfig.load(path)
    shipped = {name: presets.build(name) for name in presets.DEFAULT_LISTS}

    print(f"live menus : {path}")
    print(f"shipped    : {', '.join(presets.DEFAULT_LISTS)}")
    print(f"live here  : {', '.join(m.name for m in live.menus)}")
    if not presets._universe():
        print("!! no 3DCoat data on this machine: rows cannot be judged usable")
    print()

    differing = report(live, shipped, args.literal)
    print()
    if differing:
        print(f"{differing} of {len(presets.DEFAULT_LISTS)} shipped list(s) differ "
              f"from the live menus.")
        print("Decide row by row, edit presets.py, then run: bash tests/run_tests.sh")
        return 1
    print("the shipped lists match the live menus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
