"""
Headless test harness: a fake ``coat`` module.

3DCoat's API is unavailable outside the application, so tests inject this in
place of the real thing. It records every call so a test can assert that a click
really did execute the command it was supposed to.
"""
from __future__ import annotations

import os
import sys
import types


class FakeCoat:
    def __init__(self, documents: str):
        self.calls: list[tuple[str, str]] = []
        self._documents = documents
        self.ui = types.SimpleNamespace(cmd=self._cmd, presentInUI=lambda _id: True)
        self.io = types.SimpleNamespace(
            documents=lambda: self._documents,
            executeScript=self._script,
            step=lambda _n: 0,
        )
        self.settings = types.SimpleNamespace(
            getBool=lambda _k, default=False: default,
            getInt=lambda _k, default=0: default,
        )
        self.dialog = types.SimpleNamespace()

    def _cmd(self, cid, callback=None):
        self.calls.append(("cmd", str(cid)))
        if callback:
            callback()

    def _script(self, path):
        self.calls.append(("script", str(path)))

    def commands_run(self) -> list[str]:
        return [arg for kind, arg in self.calls if kind == "cmd"]

    def scripts_run(self) -> list[str]:
        return [arg for kind, arg in self.calls if kind == "script"]


def install_fake_coat(documents: str | None = None, source_dir: str | None = None):
    """Put a fake ``coat`` on sys.modules and return it.

    ``source_dir`` (the coat_side folder) is added to sys.path so ``core`` and
    ``ui`` import exactly as they do inside 3DCoat.
    """
    documents = documents or os.path.join(os.environ.get("TEMP", "."), "coatmenu-fake-docs")
    if source_dir and source_dir not in sys.path:
        sys.path.insert(0, source_dir)

    fake = FakeCoat(documents)
    module = types.ModuleType("coat")
    module.ui = fake.ui
    module.io = fake.io
    module.settings = fake.settings
    module.dialog = fake.dialog
    sys.modules["coat"] = module
    return fake
