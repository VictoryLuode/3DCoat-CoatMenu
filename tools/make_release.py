"""Build the release zip.

    python tools/make_release.py            # dist/CoatMenu-<version>.zip
    python tools/make_release.py 0.5.0      # override the version

What goes in is exactly what someone needs to install it: the extension, the
installer, and the docs that ship with a repo. Tests, previews and this script
stay out, so the zip has nothing machine-specific in it.

Run it from anywhere; paths are resolved from this file's location.
"""

from __future__ import annotations

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# (what to include, where it lands in the zip)
INCLUDE_DIRS = [
    ("coat_side", "CoatMenu/coat_side"),
    ("install", "CoatMenu/install"),
]
INCLUDE_FILES = ["README.md", "LICENSE", "CHANGELOG.md"]
# Never ship these, even inside an included folder.
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".log")


def version() -> str:
    """The package version, unless one was given on the command line."""
    if len(sys.argv) > 1:
        return sys.argv[1].lstrip("v")
    init = os.path.join(ROOT, "coat_side", "coatmenu", "__init__.py")
    with open(init, encoding="utf-8") as fh:
        match = re.search(r'__version__\s*=\s*"([^"]+)"', fh.read())
    if not match:
        raise SystemExit(f"No __version__ in {init}")
    return match.group(1)


def wanted(name: str) -> bool:
    return name not in SKIP_DIRS and not name.endswith(SKIP_SUFFIXES)


def main() -> int:
    tag = f"v{version()}"
    os.makedirs(DIST, exist_ok=True)
    target = os.path.join(DIST, f"CoatMenu-{tag}.zip")

    added = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, prefix in INCLUDE_DIRS:
            source = os.path.join(ROOT, folder)
            for base, dirs, files in os.walk(source):
                dirs[:] = [d for d in dirs if wanted(d)]
                for name in sorted(files):
                    if not wanted(name):
                        continue
                    full = os.path.join(base, name)
                    rel = os.path.relpath(full, source)
                    zf.write(full, os.path.join(prefix, rel).replace("\\", "/"))
                    added += 1
        for name in INCLUDE_FILES:
            full = os.path.join(ROOT, name)
            if os.path.exists(full):
                zf.write(full, f"CoatMenu/{name}")
                added += 1

    size = os.path.getsize(target) / 1024
    print(f"{target}  ({added} files, {size:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
