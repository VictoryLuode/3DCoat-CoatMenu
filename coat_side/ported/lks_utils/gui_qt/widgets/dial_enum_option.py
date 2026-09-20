"""Option model for QDialEnumPicker."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

import sys

# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode).
# ctypes only — do not hard-import pythoncom (pywin32); unavailable in 3DCoat Python.
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget


class DialEnumSizeMode(str, Enum):
    """How QDialEnumPicker resolves its outer geometry."""

    FIXED = "fixed"
    SHRINK_TO_LARGEST = "shrink_to_largest"


@dataclass(frozen=True)
class DialEnumOption:
    """One selectable row in a dial enum picker."""

    value: Any
    label: str
    leading: QIcon | QWidget | None = None
    trailing: QIcon | QWidget | None = None


def enum_display_label(member: Enum) -> str:
    """Return a display label for an enum member."""
    raw = member.value
    if isinstance(raw, str):
        return raw
    return member.name


def normalize_dial_enum_options(
    options: Sequence[str | Enum | DialEnumOption],
) -> list[DialEnumOption]:
    """Coerce shorthand strings/enums into DialEnumOption rows."""
    normalized: list[DialEnumOption] = []
    for item in options:
        if isinstance(item, DialEnumOption):
            normalized.append(item)
            continue
        if isinstance(item, Enum):
            normalized.append(
                DialEnumOption(value=item, label=enum_display_label(item))
            )
            continue
        normalized.append(DialEnumOption(value=item, label=str(item)))
    return normalized


__all__ = [
    "DialEnumOption",
    "DialEnumSizeMode",
    "enum_display_label",
    "normalize_dial_enum_options",
]
