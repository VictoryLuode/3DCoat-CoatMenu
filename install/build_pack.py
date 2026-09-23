"""
CoatMenu - build the ``.3dcpack`` release artifact.

A ``.3dcpack`` is a plain zip whose entries are paths relative to 3D-Coat's
documents folder (``Documents/3DCoat/``), i.e. they start with ``UserPrefs/``.
3D-Coat installs one from ``Addons ▸ Install Extension`` (or ``File ▸ Install
extension``) by extracting those files into that folder, which is why a pack

* **can** carry the extension (``UserPrefs/Scripts/cExtensions/CoatMenu/`` is just
  another path in the archive - there is no list of allowed folders), and
* **cannot** finish the job: it only adds/replaces *files*, so it cannot append the
  ``startup.txt`` line that switches an extension on. That switch is 3D-Coat's own
  Auto-Launch checkbox in ``Windows ▸ Panels ▸ Extensions``.

The pack carries code only - the same file set ``install.py`` copies. Everything
else (the launchers, ``ExtraMenuItems/CoatMenu.xml`` with this machine's absolute
paths, ``data/menus.json``) is written by the extension itself on first load.

Usage::

    python install/build_pack.py                    # dist/CoatMenu-<version>.3dcpack
    python install/build_pack.py --out DIR          # somewhere else
    python install/build_pack.py --extension NAME   # a renamed copy (testing)
"""
from __future__ import annotations

import argparse
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)

if HERE not in sys.path:
    sys.path.insert(0, HERE)

import install as installer  # noqa: E402  (same folder, the shipping file set)

PACK_FOLDER = os.path.join("UserPrefs", "Scripts", "cExtensions")
LICENCE = "GPL-3.0"
REPO_URL = "https://github.com/VictoryLuode/3DCoat-CoatMenu"


def extension_version() -> str:
    """``__version__`` as the shipped code declares it (the version this pack is)."""
    init = os.path.join(PROJECT_ROOT, "coat_side", "coatmenu", "__init__.py")
    with open(init, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"no __version__ in {init}")


def _readme(extension: str, version: str) -> str:
    return f"""{extension} {version} - custom menus for 3D-Coat
{'=' * (len(extension) + len(version) + 33)}

Blender-style custom menus: a pie or a list on a hotkey, a built-in list, and an
editor panel to rearrange it.

This is a 3DCoat extension package (.3dcpack). Install it in 3D-Coat with
Addons > Install Extension (older builds: File > Install extension) and pick
this file.

A package can only add or replace files, so it cannot switch the extension on
by itself. After installing, open Windows > Panels > Extensions, find
{extension} and press Start - or tick Auto-Launch so it loads with 3D-Coat from
now on. Then restart 3D-Coat once: the Scripts > {extension} entries are read
from a menu file the extension writes on its first load.

Licence: {LICENCE}. Source: {REPO_URL}
"""


def build(out_path: str, extension: str = installer.EXTENSION_NAME,
          version: str | None = None) -> str:
    """Write the pack. ``out_path`` may be a file or a directory."""
    version = version or extension_version()
    if os.path.isdir(out_path) or out_path.endswith(("/", "\\")):
        out_path = os.path.join(out_path, f"{extension}-{version}.3dcpack")
    folder = os.path.join(PACK_FOLDER, extension).replace("\\", "/") + "/"

    files = installer._iter_source_files()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for src, rel in files:
            archive.write(src, folder + rel.replace("\\", "/"))
        archive.writestr(folder + f"{extension}-README.txt", _readme(extension, version))
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="build the .3dcpack release artifact")
    parser.add_argument("--out", default=os.path.join(PROJECT_ROOT, "dist"),
                        help="output file or directory (default: <repo>/dist)")
    parser.add_argument("--extension", default=installer.EXTENSION_NAME,
                        help="extension folder name inside the pack")
    args = parser.parse_args()

    version = extension_version()
    out = args.out
    if os.path.isdir(out) or os.path.splitext(out)[1] == "":
        os.makedirs(out, exist_ok=True)
    pack = build(out, args.extension)

    with zipfile.ZipFile(pack) as archive:
        names = archive.namelist()
    print(f"{args.extension} {version}")
    print(f"wrote {pack} ({os.path.getsize(pack)} bytes, {len(names)} entries)")
    print(f"install: 3D-Coat ▸ Addons ▸ Install Extension ▸ this file")
    print(f"then   : Windows ▸ Panels ▸ Extensions ▸ {args.extension} ▸ Start / Auto-Launch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
