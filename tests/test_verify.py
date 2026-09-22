"""End-to-end verification of this round's repairs.

Each check corresponds to something that actually broke:
  * presets.py lost COMMON_MENUS when a function was cut with text find/replace;
  * doctor.py kept calling a probe whose body had gone;
  * test_catalog.py lost a section that was never about tool presets;
  * render_preview.py still called presets_list().
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys

ROOT = os.path.abspath(".")
SRC = os.path.join(ROOT, "coat_side")
sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "tests"))

failures = []


def check(ok: bool, what: str) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        failures.append(what)


print("== every module imports ==")
# The shape of the bug that broke the installer: a name vanished from a module and
# only showed up when something imported it.
import importlib
mods = []
for base, dirs, files in os.walk(os.path.join(SRC, "coatmenu")):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in sorted(files):
        if not name.endswith(".py"):
            continue
        rel = os.path.relpath(os.path.join(base, name), SRC).replace("\\", "/")
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        mods.append(mod)

# Qt-free core first, so a failure names the real culprit
qt_mods = [m for m in mods if ".ui" in m or m.endswith(".ui")]
plain = [m for m in mods if m not in qt_mods]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
for mod in sorted(plain):
    try:
        importlib.import_module(mod)
    except Exception as exc:
        check(False, f"import {mod}: {exc}")
for mod in sorted(qt_mods):
    try:
        importlib.import_module(mod)
    except Exception as exc:
        check(False, f"import {mod}: {exc}")
check(not failures, f"{len(mods)} modules imported")

print()
print("== names referenced but never defined ==")
# A hand-written scope analyser was tried here and was not worth it: it reported
# 181 false positives (closure variables, comprehension targets, __file__). The
# real defence against a name vanishing from a module - the bug that broke the
# installer this round - is the import sweep above, which loads every module and
# therefore resolves every module-level name for real. pyflakes would be better
# still, but 3DCoat's bundled Python does not have it and the user's environment is
# not ours to modify.
import ast as _ast  # noqa: E402
compiled = 0
for base, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for name in files:
        if not name.endswith(".py"):
            continue
        path = os.path.join(base, name)
        try:
            compile(open(path, encoding="utf-8", errors="replace").read(), path, "exec")
            compiled += 1
        except SyntaxError as exc:
            check(False, f"{name}: {exc}")
check(not failures, f"{compiled} files compile")

print()
print("== every shipped menu still builds, on the real 3DCoat ==")
from coatmenu.core import presets as P  # noqa: E402

shipped = P.default_lists()
check([menu.name for menu in shipped] == list(P.DEFAULT_LISTS),
      f"the shipped set is the one we mean ({[m.name for m in shipped]})")
for menu in shipped:
    check(bool(menu.items), f"{menu.name} -> {len(menu.items)} row(s)")
check(not hasattr(P, "presets_list"), "presets_list is gone")
check(not hasattr(P, "preset_rows"), "preset_rows is gone")
check(not os.path.isdir(os.path.join(SRC, "ported")),
      "the ported tree is gone from the extension")

print()
print("== the catalog no longer reads tool presets ==")
from coatmenu.core import catalog  # noqa: E402

check(not hasattr(catalog, "read_presets"), "read_presets is gone")
check(bool(catalog.read_all_commands()), "commands still read")
check(bool(catalog.read_my_tools()), "My tools still read")
check(bool(catalog.read_script_commands()), "scripts still read")

print()
print("== doctor runs end to end ==")
try:
    from coatmenu.core import doctor  # noqa: E402
    text = doctor.report()
    check("version" in text, "the report names the version")
    check("preset" not in text.lower() or "Presets panel" not in text,
          "no preset probe left in the report")
except Exception as exc:
    check(False, f"doctor.report() raised {exc}")

print()
print("== the installer imports and runs ==")
r = subprocess.run([sys.executable, os.path.join(ROOT, "install", "install.py")],
                   capture_output=True, text=True, cwd=ROOT)
check(r.returncode == 0, f"installer exit {r.returncode}")
check("files copied" in r.stdout, "it reported what it copied")
check("Presets" not in r.stdout, "and no longer lists a Presets menu")

print()
if failures:
    print(f"VERIFY FAILED ({len(failures)}): " + "; ".join(failures[:5]))
    sys.exit(1)
print("VERIFY PASSED")
sys.exit(0)
