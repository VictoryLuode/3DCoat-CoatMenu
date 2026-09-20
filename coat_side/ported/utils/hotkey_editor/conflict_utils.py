"""
Hotkey Editor - Conflict Detection Utilities

Standalone conflict detection logic used by both the main window
and the conflict resolution dialog.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..hotkey_utils import HotkeyEntry, HotkeysFile

from .styles import (
    DEFAULT_GARBAGE_KEY,
    DEFAULT_GARBAGE_CTRL,
    DEFAULT_GARBAGE_ALT,
    DEFAULT_GARBAGE_SHIFT,
)


def is_garbage_key(
    entry: "HotkeyEntry",
    garbage_key: str = DEFAULT_GARBAGE_KEY,
    garbage_ctrl: bool = DEFAULT_GARBAGE_CTRL,
    garbage_alt: bool = DEFAULT_GARBAGE_ALT,
    garbage_shift: bool = DEFAULT_GARBAGE_SHIFT,
) -> bool:
    """Check if entry uses the garbage key binding."""
    return (
        entry.code == garbage_key and
        entry.ctrl == garbage_ctrl and
        entry.alt == garbage_alt and
        entry.shift == garbage_shift
    )


def find_conflicts_with_global(
    hotkeys_file: "HotkeysFile",
    garbage_key: str = DEFAULT_GARBAGE_KEY,
    garbage_ctrl: bool = DEFAULT_GARBAGE_CTRL,
    garbage_alt: bool = DEFAULT_GARBAGE_ALT,
    garbage_shift: bool = DEFAULT_GARBAGE_SHIFT,
) -> dict[str, list["HotkeyEntry"]]:
    """
    Find conflicts including Global+Room conflicts.

    A conflict occurs when:
    - Multiple entries share the same binding in the same room
    - A room-specific entry shares a binding with a Global entry

    Returns:
        dict mapping binding_key to list of conflicting entries
    """
    # Build index: (code, ctrl, alt, shift) -> list of entries
    binding_index: dict[tuple, list["HotkeyEntry"]] = {}

    for entry in hotkeys_file.entries:
        if not entry.is_assigned:
            continue
        if entry.is_duplicate:
            continue
        # Skip garbage key entries
        if is_garbage_key(entry, garbage_key, garbage_ctrl, garbage_alt, garbage_shift):
            continue

        binding_tuple = (entry.code, entry.ctrl, entry.alt, entry.shift)
        if binding_tuple not in binding_index:
            binding_index[binding_tuple] = []
        binding_index[binding_tuple].append(entry)

    # Find conflicts
    conflicts: dict[str, list["HotkeyEntry"]] = {}

    for binding_tuple, entries in binding_index.items():
        if len(entries) < 2:
            continue

        # Group by room, but Global ("") conflicts with everything
        global_entries = [e for e in entries if e.room == ""]
        room_entries: dict[str, list["HotkeyEntry"]] = {}

        for entry in entries:
            if entry.room:
                if entry.room not in room_entries:
                    room_entries[entry.room] = []
                room_entries[entry.room].append(entry)

        # Check for conflicts
        # 1. Multiple globals = conflict
        if len(global_entries) > 1:
            key = f"|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
            if key not in conflicts:
                conflicts[key] = []
            conflicts[key].extend(global_entries)

        # 2. Multiple in same room = conflict
        for room, room_list in room_entries.items():
            if len(room_list) > 1:
                key = f"{room}|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
                if key not in conflicts:
                    conflicts[key] = []
                conflicts[key].extend(room_list)

        # 3. Global + any room-specific = conflict
        if global_entries:
            for room, room_list in room_entries.items():
                key = f"{room}+Global|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
                if key not in conflicts:
                    conflicts[key] = []
                for ge in global_entries:
                    if ge not in conflicts[key]:
                        conflicts[key].append(ge)
                for re in room_list:
                    if re not in conflicts[key]:
                        conflicts[key].append(re)

    # Filter to only actual conflicts (2+ entries with not all allow_stack)
    filtered: dict[str, list["HotkeyEntry"]] = {}
    for key, group in conflicts.items():
        if len(group) > 1 and not all(e.allow_stack for e in group):
            # Remove duplicates by id
            seen_ids = set()
            unique = []
            for e in group:
                if id(e) not in seen_ids:
                    seen_ids.add(id(e))
                    unique.append(e)
            if len(unique) > 1:
                filtered[key] = unique

    return filtered


def count_conflicts(
    hotkeys_file: "HotkeysFile",
    garbage_key: str = DEFAULT_GARBAGE_KEY,
    garbage_ctrl: bool = DEFAULT_GARBAGE_CTRL,
    garbage_alt: bool = DEFAULT_GARBAGE_ALT,
    garbage_shift: bool = DEFAULT_GARBAGE_SHIFT,
) -> int:
    """Count total number of conflict groups."""
    conflicts = find_conflicts_with_global(
        hotkeys_file, garbage_key, garbage_ctrl, garbage_alt, garbage_shift
    )
    return len(conflicts)
