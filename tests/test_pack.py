"""
Packaging tests - the `.3dcpack` release artifact.

A pack is a zip of `UserPrefs/...` paths that 3D-Coat extracts into its documents
folder, so the only things worth pinning are: it carries exactly the file set an
install copies (nothing generated, no config, no menu XML), it stays inside the
extension's own folder, and it says how to switch the extension on - 3D-Coat's
Auto-Launch, because a pack cannot append to `startup.txt`.

Run:  python tests/test_pack.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILDER = os.path.join(ROOT, "install", "build_pack.py")
sys.path.insert(0, os.path.join(ROOT, "install"))

import build_pack  # noqa: E402

failures: list[str] = []


def check(condition: bool, label: str) -> None:
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    if not condition:
        failures.append(label)


OUT = tempfile.mkdtemp(prefix="coatmenu-pack-")
version = build_pack.extension_version()

print("== build ==")
result = subprocess.run([sys.executable, BUILDER, "--out", OUT],
                        capture_output=True, text=True)
check(result.returncode == 0, f"builder exits 0 ({result.returncode}) {result.stderr.strip()}")

PACK = os.path.join(OUT, f"CoatMenu-{version}.3dcpack")
check(os.path.isfile(PACK), f"the artifact is named for the version ({os.path.basename(PACK)})")

with zipfile.ZipFile(PACK) as archive:
    names = archive.namelist()
    readme_name = [n for n in names if n.endswith("CoatMenu-README.txt")]
    readme = archive.read(readme_name[0]).decode("utf-8") if readme_name else ""

prefix = "UserPrefs/Scripts/cExtensions/CoatMenu/"
print("\n== what is inside ==")
check(all(n.startswith(prefix) for n in names), "every entry lives inside the extension folder")
check(not any("ExtraMenuItems" in n for n in names),
      "no ExtraMenuItems XML (absolute paths cannot be pre-baked)")
check(not any(n.endswith("menus.json") for n in names),
      "no menus.json (the user's own lists are never shipped)")
check(not any(n.endswith((".pyc", ".pyo")) or "__pycache__" in n for n in names),
      "no compiled leftovers")
check(not any("/actions/menus/" in n for n in names),
      "no generated launchers (they are per-user, written at install/run time)")

shipped = {rel.replace("\\", "/") for _src, rel in build_pack.installer._iter_source_files()}
inside = {n[len(prefix):] for n in names}
check(inside == shipped | {"CoatMenu-README.txt"},
      f"contents == what an install copies ({len(shipped)} files + README)")

print("\n== the file it leaves behind ==")
check(version in readme, f"the README names the version ({version})")
check("Auto-Launch" in readme and "Extensions" in readme,
      "the README says how to switch it on (Extensions ▸ Start / Auto-Launch)")
check("Install Extension" in readme, "the README says which 3D-Coat command installs it")

print("\n== a renamed copy (the on-machine test) ==")
RENAMED = tempfile.mkdtemp(prefix="coatmenu-pack-renamed-")
result = subprocess.run([sys.executable, BUILDER, "--out", RENAMED, "--extension", "CoatMenu-PackTest"],
                        capture_output=True, text=True)
check(result.returncode == 0, f"builder takes an extension name ({result.returncode})")
with zipfile.ZipFile(os.path.join(RENAMED, f"CoatMenu-PackTest-{version}.3dcpack")) as archive:
    renamed = archive.namelist()
check(all(n.startswith("UserPrefs/Scripts/cExtensions/CoatMenu-PackTest/") for n in renamed),
      "a renamed pack stays in its own folder (it cannot overwrite the real install)")
check(any(n.endswith("CoatMenu-PackTest-README.txt") for n in renamed), "with its own README")

print("\n== what 3D-Coat does with it: extract into the documents folder ==")
DOCS = tempfile.mkdtemp(prefix="coatmenu-pack-extract-")
with zipfile.ZipFile(PACK) as archive:
    archive.extractall(DOCS)
ext = os.path.join(DOCS, "UserPrefs", "Scripts", "cExtensions", "CoatMenu")
landed = {os.path.relpath(os.path.join(dirpath, name), ext).replace("\\", "/")
          for dirpath, _dirs, files in os.walk(ext) for name in files}
check(landed == inside, "extracting the pack produces the installed file tree")

print()
if failures:
    print(f"PACK FAILED ({len(failures)}): " + "; ".join(failures))
    sys.exit(1)
print("PACK TESTS PASSED")
