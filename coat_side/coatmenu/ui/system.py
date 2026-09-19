"""
CoatMenu - small Windows helpers shared by the panels.
"""
from __future__ import annotations

import ctypes
import os


def _user32():
    try:
        return ctypes.windll.user32
    except Exception:
        return None


def foreground_is_current_process() -> bool:
    """True while the foreground window belongs to this process (3DCoat).

    Our panels are always-on-top, so without this check they keep floating over
    whatever the user switched to. Once 3DCoat is no longer in front they should
    get out of the way.

    Deliberately conservative: anything we cannot determine counts as "yes", so a
    failed call can never hide a panel while the user is working in 3DCoat.
    ``COATMENU_FOREGROUND_CHECK=0`` disables the check (tests).
    """
    if os.environ.get("COATMENU_FOREGROUND_CHECK", "").strip().lower() in ("0", "false", "off", "no"):
        return True
    u = _user32()
    if u is None:
        return True
    try:
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return True
        pid = ctypes.c_ulong(0)
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return True
        return int(pid.value) == os.getpid()
    except Exception:
        return True
