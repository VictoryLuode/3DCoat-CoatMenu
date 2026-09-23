"""Build the release artifacts.

    python tools/make_release.py            # version from __init__.py
    python tools/make_release.py 0.5.3      # override the version

Two artifacts land in ``dist/``:

``CoatMenu-v<version>.zip`` - the whole story: unzip it and run
``install/install.cmd`` (which uses 3D-Coat's own Python, so nothing needs
installing first). This is the route that also prunes what a previous version left
behind, backs the user's lists up before an update, and writes the ``startup.txt``
line that loads the extension from then on.

``CoatMenu-<version>.3dcpack`` - installed from 3D-Coat itself (``Addons ▸ Install
Extension``): no archive to unzip, no Python, no unsigned ``.cmd`` for SmartScreen
to hold up. Because a pack can only add or replace *files*, the extension has to be
switched on once by hand in ``Windows ▸ Panels ▸ Extensions`` (Start, or tick
Auto-Launch) - that manual tick is why an earlier version of this script dropped the
pack. It is back because the tick is one checkbox, once, and it is the only route
that never runs a downloaded script; both are shipped, documented in README.md.

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
        # `actions/menus/` is written from the *user's* config at install and at run
        # time; whatever is in the checkout is a leftover from a test run. It is
        # already excluded from what an install copies (install._iter_source_files),
        # so it must not ride along in the archive either.
        if os.path.relpath(base, source).replace("\\", "/").startswith("actions/menus"):
            continue
        for name in sorted(files):
            if not wanted(name):
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, source)
            zf.write(full, os.path.join(prefix, rel).replace("\\", "/"))
            added += 1
    return added


def build_zip(tag: str) -> tuple[str, int]:
    """Unzip, then run install/install.cmd."""
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


def main() -> int:
    tag = version()
    os.makedirs(DIST, exist_ok=True)
    target, added = build_zip(tag)
    size = os.path.getsize(target) / 1024
    print(f"{target}  ({added} files, {size:.0f} KB)")

    sys.path.insert(0, os.path.join(ROOT, "install"))
    import build_pack
    pack = build_pack.build(os.path.join(DIST, f"{EXTENSION_NAME}-{tag}.3dcpack"),
                            version=tag)
    with zipfile.ZipFile(pack) as archive:
        entries = len(archive.namelist())
    print(f"{pack}  ({entries} entries, {os.path.getsize(pack) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

