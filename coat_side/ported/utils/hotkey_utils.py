"""
Hotkey utilities for parsing, validating, and editing 3DCoat hotkeys.

3DCoat stores hotkeys in Options_Hotkeys.xml. This file can become malformed
or contain duplicate entries, requiring regex-based parsing instead of XML.

This module provides:
- HotkeyEntry dataclass for structured hotkey data
- Parsing functions (regex-based to handle malformed XML)
- Deduplication and conflict detection
- Room validation against known 3DCoat rooms
- Versioned backup management
- XML reconstruction for saving

Usage:
    from ported.utils.hotkey_utils import (
        parse_hotkeys_file,
        find_duplicates,
        find_conflicts,
        save_hotkeys_file,
    )
    
    entries = parse_hotkeys_file(path)
    duplicates = find_duplicates(entries)
    conflicts = find_conflicts(entries)
"""
from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

# Import the authoritative keycode mapping for display conversion
from .keycode_map import (
    KEY_UNASSIGNED,
    get_display_key as _keycode_get_display_key,
    COAT_TO_DISPLAY,
)

# =============================================================================
# CONSTANTS
# =============================================================================

# Known valid 3DCoat rooms
VALID_ROOMS: frozenset[str] = frozenset({
    "",        # Global (empty = all rooms)
    "Sculpt",
    "Voxels",
    "Paint",
    "Retopo",
    "Tweak",
    "UV",
    "Render",
})

# Backup folder name
BACKUP_FOLDER: str = "hotkey_backups"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class HotkeyEntry:
    """
    Represents a single hotkey entry from Options_Hotkeys.xml.

    Attributes:
        id: Command identifier (e.g., "UNDO", "$DecimateToRetopo")
        room: Room context ("" = global, or room name like "Sculpt")
        code: Key code (e.g., "A", "CTRL", "key_00" for unassigned)
        ctrl: Ctrl modifier required
        alt: Alt modifier required
        shift: Shift modifier required
        allow_stack: Allow multiple bindings for this command
        user_defined: 0=default, 1+=user-modified

        # Computed/validation fields (set by validation functions)
        is_duplicate: True if this entry is an exact duplicate
        is_orphan_room: True if room is not in VALID_ROOMS
        conflict_ids: List of other command IDs with same binding
        line_index: Original line index in file (for reference)
    """
    id: str
    room: str = ""
    code: str = KEY_UNASSIGNED
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    allow_stack: bool = False
    user_defined: int = 0

    # Validation fields
    is_duplicate: bool = False
    is_orphan_room: bool = False
    conflict_ids: list[str] = field(default_factory=list)
    line_index: int = 0

    @property
    def is_assigned(self) -> bool:
        """Check if this hotkey has an actual key binding."""
        return self.code != KEY_UNASSIGNED

    @property
    def modifier_string(self) -> str:
        """Get human-readable modifier string (e.g., 'Ctrl+Alt')."""
        mods: list[str] = []
        if self.ctrl:
            mods.append("Ctrl")
        if self.alt:
            mods.append("Alt")
        if self.shift:
            mods.append("Shift")
        return "+".join(mods) if mods else ""

    @property
    def binding_key(self) -> str:
        """
        Get unique key for this binding (for conflict detection).

        Format: "Room|Code|Ctrl|Alt|Shift"
        Entries with same binding_key are conflicts (unless allow_stack).
        """
        return f"{self.room}|{self.code}|{self.ctrl}|{self.alt}|{self.shift}"

    @property
    def signature(self) -> tuple:
        """
        Get full signature for duplicate detection.

        All fields must match for entries to be considered exact duplicates.
        Note: UserDefined is excluded - it's just a version counter.
        """
        return (
            self.id,
            self.room,
            self.code,
            self.ctrl,
            self.alt,
            self.shift,
            self.allow_stack,
        )

    def to_xml(self) -> str:
        """
        Serialize entry to 3DCoat's quirky XML format.

        NOTE: 3DCoat uses non-standard XML:
        - Code field contains entities like `&gt` WITHOUT trailing semicolon
        - We preserve this format exactly as 3DCoat expects it
        - Standard XML parsers will reject this, but 3DCoat requires it
        """
        # Escape XML special characters in ID and Room fields
        escaped_id = html.escape(self.id, quote=False)
        escaped_room = html.escape(self.room, quote=False)
        # Code field: Pass through as-is - 3DCoat uses its own entity format
        # (e.g., &gt without semicolon for ">" key)

        return f"""		<OneHotKey>
			<ID>{escaped_id}</ID>
			<Room>{escaped_room}</Room>
			<Code>{self.code}</Code>
			<Ctrl>{str(self.ctrl).lower()}</Ctrl>
			<Alt>{str(self.alt).lower()}</Alt>
			<Shift>{str(self.shift).lower()}</Shift>
			<AllowStack>{str(self.allow_stack).lower()}</AllowStack>
			<UserDefined>{self.user_defined}</UserDefined>
		</OneHotKey>"""

    @property
    def display_key(self) -> str:
        """Human-readable key binding string using proper display names."""
        if not self.is_assigned:
            return "(unassigned)"
        parts: list[str] = []
        if self.ctrl:
            parts.append("Ctrl")
        if self.alt:
            parts.append("Alt")
        if self.shift:
            parts.append("Shift")
        # Use the keycode_map to get proper display name
        # This handles special cases like ">" displaying as "." when Shift=false
        key_display = _keycode_get_display_key(self.code, self.shift)
        parts.append(key_display)
        return "+".join(parts)

    @property
    def display_room(self) -> str:
        """Human-readable room string."""
        return self.room if self.room else "(Global)"

    def has_issues(self) -> bool:
        """Check if entry has any issues (duplicate, orphan, conflict)."""
        return self.is_duplicate or self.is_orphan_room or len(self.conflict_ids) > 0


@dataclass
class HotkeysFile:
    """
    Container for a parsed hotkeys file.

    Attributes:
        path: Path to the source file
        entries: List of parsed hotkey entries
        header: XML content before <HotKeys> section
        footer: XML content after </HotKeys> section
        parse_errors: Any errors encountered during parsing
    """
    path: Path
    entries: list[HotkeyEntry] = field(default_factory=list)
    header: str = ""
    footer: str = ""
    parse_errors: list[str] = field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def assigned_count(self) -> int:
        return sum(1 for e in self.entries if e.is_assigned)

    @property
    def duplicate_count(self) -> int:
        return sum(1 for e in self.entries if e.is_duplicate)

    @property
    def orphan_room_count(self) -> int:
        return sum(1 for e in self.entries if e.is_orphan_room)

    @property
    def conflict_count(self) -> int:
        return sum(1 for e in self.entries if len(e.conflict_ids) > 0)

    def get_unique_rooms(self) -> set[str]:
        """Get all unique rooms in the file."""
        return {e.room for e in self.entries}

    def get_entries_by_room(self, room: str) -> list[HotkeyEntry]:
        """Get entries filtered by room."""
        return [e for e in self.entries if e.room == room]

    def get_entries_with_issues(self) -> list[HotkeyEntry]:
        """Get entries that have any issues."""
        return [e for e in self.entries if e.has_issues()]


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    duplicates_removed: int = 0
    orphan_rooms_found: int = 0
    conflicts_found: int = 0
    backup_path: Path | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def _parse_bool(value: str) -> bool:
    """Parse boolean string (handles 'true'/'false' and empty)."""
    return value.lower() == "true"


def _parse_int(value: str) -> int:
    """Parse integer string (handles empty as 0)."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def parse_hotkeys_file(path: Path | str) -> HotkeysFile:
    """
    Parse a 3DCoat hotkeys XML file.

    Uses regex-based parsing to handle potentially malformed XML.

    Args:
        path: Path to Options_Hotkeys.xml

    Returns:
        HotkeysFile with parsed entries and metadata
    """
    path = Path(path)
    result = HotkeysFile(path=path)

    if not path.exists():
        result.parse_errors.append(f"File not found: {path}")
        return result

    try:
        content: str = path.read_text(encoding="utf-8")
    except Exception as e:
        result.parse_errors.append(f"Failed to read file: {e}")
        return result

    # Extract header and footer
    hotkeys_start = content.find("<HotKeys>")
    hotkeys_end = content.find("</HotKeys>")

    if hotkeys_start == -1 or hotkeys_end == -1:
        result.parse_errors.append("Could not find <HotKeys> section")
        return result

    result.header = content[:hotkeys_start + len("<HotKeys>")]
    result.footer = content[hotkeys_end:]

    # Parse individual entries using regex (handles malformed XML)
    pattern = r'<OneHotKey>(.*?)</OneHotKey>'
    matches = re.findall(pattern, content, re.DOTALL)

    for idx, match in enumerate(matches):
        if not match.strip():
            continue

        # Extract fields
        id_match = re.search(r'<ID>(.*?)</ID>', match)
        if not id_match:
            result.parse_errors.append(f"Entry {idx}: Missing ID field")
            continue

        entry = HotkeyEntry(
            # Decode HTML entities like &gt;
            id=html.unescape(id_match.group(1)),
            line_index=idx,
        )

        # Extract optional fields
        room_match = re.search(r'<Room>(.*?)</Room>', match)
        entry.room = html.unescape(room_match.group(1)) if room_match else ""

        # Code field: Don't unescape - HTML entities like &gt; are actual key codes in 3DCoat
        code_match = re.search(r'<Code>(.*?)</Code>', match)
        entry.code = code_match.group(1) if code_match else KEY_UNASSIGNED

        ctrl_match = re.search(r'<Ctrl>(.*?)</Ctrl>', match)
        entry.ctrl = _parse_bool(ctrl_match.group(1)) if ctrl_match else False

        alt_match = re.search(r'<Alt>(.*?)</Alt>', match)
        entry.alt = _parse_bool(alt_match.group(1)) if alt_match else False

        shift_match = re.search(r'<Shift>(.*?)</Shift>', match)
        entry.shift = _parse_bool(
            shift_match.group(1)) if shift_match else False

        allow_stack_match = re.search(r'<AllowStack>(.*?)</AllowStack>', match)
        entry.allow_stack = _parse_bool(
            allow_stack_match.group(1)) if allow_stack_match else False

        user_defined_match = re.search(
            r'<UserDefined>(.*?)</UserDefined>', match)
        entry.user_defined = _parse_int(
            user_defined_match.group(1)) if user_defined_match else 0

        result.entries.append(entry)

    return result


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def find_duplicates(entries: list[HotkeyEntry]) -> list[HotkeyEntry]:
    """
    Find exact duplicate entries.

    Marks entries with is_duplicate=True if they are duplicates of an earlier entry.
    Returns list of duplicate entries (not the original of each set).

    Args:
        entries: List of hotkey entries to check

    Returns:
        List of duplicate entries (the later occurrences)
    """
    seen_signatures: set[tuple] = set()
    duplicates: list[HotkeyEntry] = []

    for entry in entries:
        signature = entry.signature
        if signature in seen_signatures:
            entry.is_duplicate = True
            duplicates.append(entry)
        else:
            seen_signatures.add(signature)

    return duplicates


def find_conflicts(entries: list[HotkeyEntry]) -> dict[str, list[HotkeyEntry]]:
    """
    Find hotkey conflicts (same binding in same room, different commands).

    Updates conflict_ids on affected entries.

    Args:
        entries: List of hotkey entries to check

    Returns:
        Dict mapping binding_key to list of conflicting entries
    """
    # Group by binding key (only assigned hotkeys)
    binding_to_entries: dict[str, list[HotkeyEntry]] = {}

    for entry in entries:
        if not entry.is_assigned:
            continue
        if entry.is_duplicate:
            continue  # Skip duplicates

        key = entry.binding_key
        if key not in binding_to_entries:
            binding_to_entries[key] = []
        binding_to_entries[key].append(entry)

    # Find conflicts (multiple entries with same binding)
    conflicts: dict[str, list[HotkeyEntry]] = {}

    for binding_key, group in binding_to_entries.items():
        if len(group) > 1:
            # Check if all allow stacking - if so, not a conflict
            if all(e.allow_stack for e in group):
                continue

            conflicts[binding_key] = group
            # Update entries with conflict info
            for entry in group:
                entry.conflict_ids = [e.id for e in group if e.id != entry.id]

    return conflicts


def find_orphan_rooms(
    entries: list[HotkeyEntry],
    valid_rooms: frozenset[str] | None = None,
) -> list[HotkeyEntry]:
    """
    Find entries with rooms not in the valid rooms list.

    Marks entries with is_orphan_room=True.

    Args:
        entries: List of hotkey entries to check
        valid_rooms: Set of valid room names (default: VALID_ROOMS)

    Returns:
        List of entries with orphan rooms
    """
    if valid_rooms is None:
        valid_rooms = VALID_ROOMS

    orphans: list[HotkeyEntry] = []

    for entry in entries:
        if entry.room and entry.room not in valid_rooms:
            entry.is_orphan_room = True
            orphans.append(entry)

    return orphans


def validate_all(
    hotkeys_file: HotkeysFile,
    valid_rooms: frozenset[str] | None = None,
) -> None:
    """
    Run all validation checks on a hotkeys file.

    Updates entries in-place with validation flags.

    Args:
        hotkeys_file: Parsed hotkeys file
        valid_rooms: Set of valid room names (optional)
    """
    find_duplicates(hotkeys_file.entries)
    find_conflicts(hotkeys_file.entries)
    find_orphan_rooms(hotkeys_file.entries, valid_rooms)


# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

def remove_duplicates(entries: list[HotkeyEntry]) -> tuple[list[HotkeyEntry], int]:
    """
    Remove exact duplicate entries, keeping only the first occurrence.

    Args:
        entries: List of hotkey entries

    Returns:
        Tuple of (unique entries list, count of removed duplicates)
    """
    seen_signatures: set[tuple] = set()
    unique: list[HotkeyEntry] = []
    removed_count: int = 0

    for entry in entries:
        signature = entry.signature
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique.append(entry)
        else:
            removed_count += 1

    return unique, removed_count


def remove_orphan_rooms(
    entries: list[HotkeyEntry],
    valid_rooms: frozenset[str] | None = None,
) -> tuple[list[HotkeyEntry], int]:
    """
    Remove entries with rooms not in the valid rooms list.

    Args:
        entries: List of hotkey entries
        valid_rooms: Set of valid room names (default: VALID_ROOMS)

    Returns:
        Tuple of (filtered entries list, count of removed entries)
    """
    if valid_rooms is None:
        valid_rooms = VALID_ROOMS

    filtered: list[HotkeyEntry] = []
    removed_count: int = 0

    for entry in entries:
        if entry.room and entry.room not in valid_rooms:
            removed_count += 1
        else:
            filtered.append(entry)

    return filtered, removed_count


# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

def get_backup_dir(hotkeys_path: Path) -> Path:
    """Get the backup directory for a hotkeys file."""
    return hotkeys_path.parent / BACKUP_FOLDER


def create_backup(
    hotkeys_path: Path,
) -> Path:
    """
    Create a versioned backup of the hotkeys file.

    Backups are stored in hotkey_backups/ subfolder with timestamp names.
    All backups are kept indefinitely.

    Args:
        hotkeys_path: Path to the hotkeys file

    Returns:
        Path to the created backup file
    """
    hotkeys_path = Path(hotkeys_path)
    backup_dir = get_backup_dir(hotkeys_path)
    backup_dir.mkdir(exist_ok=True)

    # Create timestamped backup
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name: str = f"Options_Hotkeys_{timestamp}.xml"
    backup_path: Path = backup_dir / backup_name

    shutil.copy2(hotkeys_path, backup_path)

    return backup_path


def list_backups(hotkeys_path: Path) -> list[Path]:
    """
    List existing backups for a hotkeys file.

    Returns list sorted by modification time (newest first).
    """
    backup_dir = get_backup_dir(hotkeys_path)
    if not backup_dir.exists():
        return []

    backups: list[Path] = sorted(
        backup_dir.glob("Options_Hotkeys_*.xml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return backups


def restore_backup(backup_path: Path, hotkeys_path: Path) -> None:
    """
    Restore a backup to the hotkeys file location.

    Creates a backup of the current file first.
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    # Backup current before restoring
    create_backup(hotkeys_path)

    # Restore
    shutil.copy2(backup_path, hotkeys_path)


# =============================================================================
# SAVE FUNCTIONS
# =============================================================================

def reconstruct_xml(hotkeys_file: HotkeysFile) -> str:
    """
    Reconstruct the XML content from a HotkeysFile.

    Uses the original header/footer and regenerates the entries section.
    """
    entries_xml: list[str] = [entry.to_xml() for entry in hotkeys_file.entries]
    return hotkeys_file.header + "\n" + "\n".join(entries_xml) + "\n\t" + hotkeys_file.footer


def save_hotkeys_file(
    hotkeys_file: HotkeysFile,
    path: Path | None = None,
    create_backup_first: bool = True,
) -> Path | None:
    """
    Save a HotkeysFile to disk in 3DCoat's quirky XML format.

    NOTE: 3DCoat uses non-standard XML with malformed entities like `&gt` and `&lt`
    (missing trailing semicolon). Standard XML parsers reject this, but 3DCoat
    REQUIRES this format. We skip XML validation and write directly.

    Args:
        hotkeys_file: The hotkeys file to save
        path: Output path (default: original path)
        create_backup_first: Create backup before saving

    Returns:
        Backup path if created, None otherwise
    """
    save_path: Path = path or hotkeys_file.path
    backup_path: Path | None = None

    if create_backup_first and save_path.exists():
        backup_path = create_backup(save_path)

    content: str = reconstruct_xml(hotkeys_file)

    # NOTE: We intentionally skip XML validation here.
    # 3DCoat uses malformed entities like &gt and &lt (no semicolon)
    # which are invalid per XML spec but required by 3DCoat.

    save_path.write_text(content, encoding="utf-8")

    return backup_path


def validate_xml_string(xml_content: str) -> tuple[bool, str | None]:
    """
    Validate XML string for standard XML well-formedness.

    WARNING: This uses standard XML parsing which will REJECT 3DCoat's
    quirky format (e.g., `&gt` without semicolon). Do NOT use this to
    validate 3DCoat hotkey files - they are intentionally non-standard.

    Args:
        xml_content: XML string to validate

    Returns:
        (is_valid, error_message) tuple
    """
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(xml_content)
        return (True, None)
    except ET.ParseError as e:
        return (False, str(e))


# =============================================================================
# STATISTICS FUNCTIONS
# =============================================================================

@dataclass
class HotkeyStats:
    """Statistics about a hotkeys file."""
    total_entries: int = 0
    assigned_entries: int = 0
    unassigned_entries: int = 0
    user_modified: int = 0
    default_bindings: int = 0
    unique_rooms: int = 0
    rooms: list[str] = field(default_factory=list)
    duplicates: int = 0
    conflicts: int = 0
    orphan_rooms: int = 0

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "assigned_entries": self.assigned_entries,
            "unassigned_entries": self.unassigned_entries,
            "user_modified": self.user_modified,
            "default_bindings": self.default_bindings,
            "unique_rooms": self.unique_rooms,
            "rooms": self.rooms,
            "duplicates": self.duplicates,
            "conflicts": self.conflicts,
            "orphan_rooms": self.orphan_rooms,
        }


def get_stats(hotkeys_file: HotkeysFile) -> HotkeyStats:
    """Calculate statistics for a hotkeys file."""
    stats = HotkeyStats()

    stats.total_entries = len(hotkeys_file.entries)
    stats.assigned_entries = sum(
        1 for e in hotkeys_file.entries if e.is_assigned)
    stats.unassigned_entries = stats.total_entries - stats.assigned_entries
    stats.user_modified = sum(
        1 for e in hotkeys_file.entries if e.user_defined > 0)
    stats.default_bindings = stats.total_entries - stats.user_modified

    rooms = hotkeys_file.get_unique_rooms()
    stats.unique_rooms = len(rooms)
    stats.rooms = sorted(r if r else "(Global)" for r in rooms)

    stats.duplicates = sum(1 for e in hotkeys_file.entries if e.is_duplicate)
    stats.conflicts = sum(
        1 for e in hotkeys_file.entries if len(e.conflict_ids) > 0)
    stats.orphan_rooms = sum(
        1 for e in hotkeys_file.entries if e.is_orphan_room)

    return stats


# =============================================================================
# PATH HELPERS
# =============================================================================

def get_default_hotkeys_path() -> Path | None:
    """
    Get the default hotkeys file path.

    Uses coat.io.documents() if available (inside 3DCoat),
    otherwise returns None.
    """
    try:
        import coat
        docs_path: str = coat.io.documents("")
        return Path(docs_path) / "UserPrefs" / "Preferences" / "Options_Hotkeys.xml"
    except ImportError:
        return None


def discover_hotkeys_path(search_paths: list[Path] | None = None) -> Path | None:
    """
    Discover the hotkeys file path.

    Tries 3DCoat API first, then searches common locations.

    Args:
        search_paths: Additional paths to search

    Returns:
        Path to hotkeys file if found, None otherwise
    """
    # Try 3DCoat API first
    coat_path = get_default_hotkeys_path()
    if coat_path and coat_path.exists():
        return coat_path

    # Search common locations
    common_locations: list[Path] = [
        Path.home() / "Documents" / "3DCoat" / "UserPrefs" /
        "Preferences" / "Options_Hotkeys.xml",
        Path.home() / "Documents" / "3DCoat-2025" / "UserPrefs" /
        "Preferences" / "Options_Hotkeys.xml",
    ]

    if search_paths:
        common_locations.extend(search_paths)

    for path in common_locations:
        if path.exists():
            return path

    return None
