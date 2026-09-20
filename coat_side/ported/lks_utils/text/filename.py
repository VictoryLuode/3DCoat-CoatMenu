"""
Filename utilities.
Provides sanitization and validation functions for filenames.
"""
from __future__ import annotations

import os
from pathlib import Path

from ported.lks_utils.text.sanitization import clamp_length, ensure_non_empty, normalize_whitespace_and_underscores, remove_emojis_and_symbols, remove_filesystem_unsafe_chars, remove_multiple_periods, remove_non_ascii_chars, remove_ytdlp_format_codes, sanitize_reserved_names, strip_leading_trailing_chars, convert_fullwidth_to_ascii


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove problematic characters and ensure filesystem compatibility.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "file"

    # Use utility functions for clean, focused sanitization
    sanitized = remove_filesystem_unsafe_chars(filename)
    sanitized = normalize_whitespace_and_underscores(sanitized)
    sanitized = strip_leading_trailing_chars(sanitized, "._")
    sanitized = clamp_length(sanitized, 200)
    sanitized = ensure_non_empty(sanitized, "file")

    return sanitized


def sanitize_video_filename(filename: str) -> str:
    """Enhanced sanitization for video filenames with comprehensive character handling.

    Args:
        filename: The video filename to sanitize

    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "video"

    # Convert to string if not already
    filename = str(filename)

    # Use utility functions for clean, step-by-step sanitization
    sanitized = remove_ytdlp_format_codes(filename)
    sanitized = remove_filesystem_unsafe_chars(sanitized)
    sanitized = remove_emojis_and_symbols(sanitized)
    sanitized = remove_non_ascii_chars(sanitized)
    sanitized = convert_fullwidth_to_ascii(sanitized)
    sanitized = normalize_whitespace_and_underscores(sanitized)
    sanitized = remove_multiple_periods(sanitized)
    sanitized = strip_leading_trailing_chars(sanitized, "._-")
    sanitized = clamp_length(sanitized, 180, preserve_extension=True)
    sanitized = sanitize_reserved_names(sanitized)
    sanitized = ensure_non_empty(sanitized, "video")

    return sanitized


def normalize_filename_for_comparison(filename: str) -> str:
    """Normalize filename for comparison purposes.
    
    Applies the same transformations as sanitize_filename for consistent matching.

    Args:
        filename: The filename to normalize

    Returns:
        Normalized filename for comparison
    """
    return sanitize_filename(filename).lower()


def find_existing_file_by_title(
    output_path: str,
    title: str,
    extensions: list[str] | None = None
) -> str | None:
    """Check if a file with the same sanitized title already exists in the directory.

    Args:
        output_path: Directory to search in
        title: Title to search for (will be sanitized)
        extensions: List of extensions to check (e.g., ['.mp4', '.webm'])

    Returns:
        Full path to existing file if found, None otherwise
    """
    if not output_path or not title or not Path(output_path).exists():
        return None

    if extensions is None:
        extensions = [".mp4", ".webm", ".mkv", ".avi", ".mov"]

    normalized_title = normalize_filename_for_comparison(title)

    try:
        for file in os.listdir(output_path):
            file_path = Path(output_path) / file
            if not Path(file_path).is_file():
                continue

            # Check extension
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext not in extensions:
                continue

            # Compare normalized names
            file_name = os.path.splitext(file)[0]
            if normalize_filename_for_comparison(file_name) == normalized_title:
                return file_path

    except Exception:
        pass

    return None


def generate_unique_filename(
    base_path: str,
    base_name: str,
    extension: str,
    max_attempts: int = 1000
) -> str:
    """Generate a unique filename by appending _1, _2, etc. if needed.

    Args:
        base_path: Directory for the file
        base_name: Base filename (without extension)
        extension: File extension (with or without leading dot)
        max_attempts: Maximum suffix attempts before giving up

    Returns:
        Unique filename (just the name, not full path)

    Raises:
        ValueError: If unable to find unique name within max_attempts
    """
    if not extension.startswith("."):
        extension = "." + extension

    # Try original name first
    candidate = f"{base_name}{extension}"
    if not Path(Path(base_path).exists() / candidate):
        return candidate

    # Try with suffix
    for i in range(1, max_attempts + 1):
        candidate = f"{base_name}_{i}{extension}"
        if not Path(Path(base_path).exists() / candidate):
            return candidate

    raise ValueError(f"Could not generate unique filename after {max_attempts} attempts")
