"""Windows key-state helpers for fast, reliable trigger detection."""

from __future__ import annotations

import sys

IS_WINDOWS: bool = sys.platform == "win32"

VK_SHIFT: int = 0x10
VK_CONTROL: int = 0x11
VK_MENU: int = 0x12


def qt_key_to_vk(qt_key: int | None) -> int | None:
    """Convert a Qt key constant to a Win32 virtual-key code."""
    if qt_key is None:
        return None

    if 0x41 <= qt_key <= 0x5A:
        return qt_key
    if 0x30 <= qt_key <= 0x39:
        return qt_key
    if 0x01000030 <= qt_key <= 0x01000047:
        return 0x70 + (qt_key - 0x01000030)

    mapping: dict[int, int] = {
        0x20: 0x20,
        0x09: 0x09,
        0x01000004: 0x0D,
        0x01000000: 0x1B,
        0x01000007: 0x2E,
        0x01000010: 0x24,
        0x01000016: 0x21,
        0x01000017: 0x22,
        0x01000006: 0x2D,
        0x01000013: 0x26,
        0x01000015: 0x28,
        0x01000012: 0x25,
        0x01000014: 0x27,
        0x60: 0xC0,
        0x7E: 0xC0,
        0x2D: 0xBD,
        0x3D: 0xBB,
        0x5B: 0xDB,
        0x5D: 0xDD,
        0x5C: 0xDC,
        0x3B: 0xBA,
        0x27: 0xDE,
        0x2C: 0xBC,
        0x2E: 0xBE,
        0x2F: 0xBF,
        0x01000020: VK_SHIFT,
        0x01000021: VK_CONTROL,
        0x01000023: VK_MENU,
    }
    return mapping.get(qt_key)


def is_vk_down(vk_code: int | None) -> bool:
    """Return True when the given virtual-key is physically pressed."""
    if not IS_WINDOWS or vk_code is None:
        return False

    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
    except Exception:
        return False


def binding_is_active(
    qt_key: int | None,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
) -> bool:
    """Return True when the main key and exact modifier state match."""
    vk_code: int | None = qt_key_to_vk(qt_key)
    if not is_vk_down(vk_code):
        return False

    return (
        is_vk_down(VK_CONTROL) == ctrl
        and is_vk_down(VK_MENU) == alt
        and is_vk_down(VK_SHIFT) == shift
    )
