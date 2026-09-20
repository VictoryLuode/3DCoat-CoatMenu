"""Build the release artifacts.

    python tools/make_release.py            # both, version from __init__.py
    python tools/make_release.py 0.5.0      # override the version

Two files come out in ``dist/``:

* ``CoatMenu-v<version>.zip`` - the repository-style archive: unzip it and run
  ``install/install.cmd``.
* ``CoatMenu-v<version>.3dcpack`` - 3D-Coat's own package format. It is a plain
  zip whose entries are ``UserPrefs/``-relative paths, installed with
  ``File > Install > Install extension``. Nothing to run by hand.

Two things are deliberately kept out of the .3dcpack:

* ``startup.txt`` - the package would *replace* 3DCoat's auto-launch list and wipe
  every other extension's line out of it. The user ticks Auto-Launch in
  ``Windows > Panels > Extensions`` instead, which is 3DCoat's own mechanism.
* the generated launchers and the menu XML - they depend on the user's config and
  contain absolute paths, so the extension writes them itself on first start.

Run it from anywhere; paths are resolved from this file's location.
"""

from __future__ import annotations

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

EXTENSION_NAME = "CoatMenu"

# (what to include, where it lands in the archive)
INCLUDE_DIRS = [
    ("coat_side", "CoatMenu/coat_side"),
    ("install", "CoatMenu/install"),
]
INCLUDE_FILES = ["README.md", "LICENSE", "CHANGELOG.md"]
# Never ship these, even inside an included folder.
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "dist"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".log")

# Where the extension lands once 3DCoat unpacks the package.
PACK_EXTENSION_DIR = f"UserPrefs/Scripts/cExtensions/{EXTENSION_NAME}"

_PACK_README = """{name} {version} for 3D-Coat 2025
{underline}

A menu belt for 3D-Coat: build your own menus out of 3D-Coat commands, tools,
presets and scripts, then reach them from a hotkey at the cursor - as a list or as
a Blender-style pie.

Install
-------
1.  File > Install > Install extension, and pick this file.
2.  Windows > Panels > Extensions - tick Auto-Launch for {name}. (Its files are in
    place after step 1, but 3D-Coat only loads extensions it is told to start.)
3.  Restart 3D-Coat, then open Scripts > {name} > Show {name}.

Keys
----
* Every menu takes a key in Edit menus > Key - 3D-Coat applies it on the next start.
* A single row takes its own key by right-clicking it > Set key. Only rows with a
  key appear in the Scripts menu.
* Keys you set by hand in Preferences > Hotkeys are never overridden.

Your menus
----------
They live in

    UserPrefs/Scripts/cExtensions/{name}/data/menus.json

Copy that file to carry your setup to another machine.

License: GPL-3.0.  Source: https://github.com/VictoryLuode/3DCoat-{name}
"""


def version() -> str:
    """The package version, unless one was given on the command line."""
    given = [a for a in sys.argv[1:] if not a.startswith("-")]
    if given:
        return given[0].lstrip("v")
    init = os.path.join(ROOT, "coat_side", "coatmenu", "__init__.py")
    with open(init, encoding="utf-8") as fh:
        match = re.search(r'__version__\s*=\s*"([^"]+)"', fh.read())
    if not match:
        raise SystemExit(f"No __version__ in {init}")
    return match.group(1)


def wanted(name: str) -> bool:
    return name not in SKIP_DIRS and not name.endswith(SKIP_SUFFIXES)


def _add_tree(zf: zipfile.ZipFile, source: str, prefix: str) -> int:
    """Copy one folder into the archive, preserving its shape."""
    added = 0
    for base, dirs, files in os.walk(source):
        dirs[:] = [d for d in dirs if wanted(d)]
        for name in sorted(files):
            if not wanted(name):
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, source)
            zf.write(full, os.path.join(prefix, rel).replace("\\", "/"))
            added += 1
    return added


def build_zip(tag: str) -> tuple[str, int]:
    """The repository-style archive: unzip and run the installer."""
    target = os.path.join(DIST, f"{EXTENSION_NAME}-v{tag}.zip")
    added = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, prefix in INCLUDE_DIRS:
            added += _add_tree(zf, os.path.join(ROOT, folder), prefix)
        for name in INCLUDE_FILES:
            full = os.path.join(ROOT, name)
            if os.path.exists(full):
                zf.write(full, f"{EXTENSION_NAME}/{name}")
                added += 1
    return target, added


def build_pack(tag: str) -> tuple[str, int]:
    """The .3dcpack: installable through 3D-Coat's own File > Install extension."""
    target = os.path.join(DIST, f"{EXTENSION_NAME}-v{tag}.3dcpack")
    added = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        added += _add_tree(zf, os.path.join(ROOT, "coat_side"), PACK_EXTENSION_DIR)
        title = f"{EXTENSION_NAME} v{tag} for 3D-Coat 2025"
        body = _PACK_README.format(name=EXTENSION_NAME, version=f"v{tag}",
                                  underline="-" * len(title))
        zf.writestr(f"{EXTENSION_NAME}-README.txt", body)
        added += 1
    return target, added


def main() -> int:
    tag = version()
    os.makedirs(DIST, exist_ok=True)

    for build in (build_zip, build_pack):
        target, added = build(tag)
        size = os.path.getsize(target) / 1024
        print(f"{target}  ({added} files, {size:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
