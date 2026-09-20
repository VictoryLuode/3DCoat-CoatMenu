"""
String sanitization utilities.
Provides focused, single-purpose sanitization functions that can be composed together.
"""
from __future__ import annotations

import re
import unicodedata
from enum import Enum


class SpaceHandlingMode(str, Enum):
    """How to handle spaces during text processing."""
    KEEP_AS_UNDERSCORE = "keep_as_underscore"
    REMOVE_SPACES = "remove_spaces"
    KEEP_SPACES = "keep_spaces"


# Common default values
DEFAULT_REPLACEMENT_CHAR: str = "_"
DEFAULT_MAX_LENGTH: int = 255
DEFAULT_MIN_NAME_LENGTH: int = 10


def handle_spaces(text: str, mode: str | SpaceHandlingMode = SpaceHandlingMode.KEEP_AS_UNDERSCORE) -> str:
    """Handle spaces in text according to specified mode.

    Args:
        text: The text to process
        mode: How to handle spaces:
            - "keep_as_underscore": Convert spaces to underscores (default)
            - "remove_spaces": Remove all spaces and underscores
            - "keep_spaces": Keep spaces as-is

    Returns:
        Processed text
    """
    if not text:
        return text

    # Convert enum to string value if needed
    mode_value: str = mode.value if isinstance(
        mode, SpaceHandlingMode) else mode

    if mode_value == SpaceHandlingMode.REMOVE_SPACES.value:
        return text.replace(" ", "").replace(DEFAULT_REPLACEMENT_CHAR, "")
    elif mode_value == SpaceHandlingMode.KEEP_SPACES.value:
        # Convert underscores back to spaces if they seem to be converted spaces
        return text.replace(DEFAULT_REPLACEMENT_CHAR, " ")
    else:  # KEEP_AS_UNDERSCORE (default)
        return text.replace(" ", DEFAULT_REPLACEMENT_CHAR)


def clamp_length(text: str, max_length: int = 255, preserve_extension: bool = True) -> str:
    """Limit text length, optionally preserving file extensions.

    Args:
        text: The text to clamp
        max_length: Maximum allowed length
        preserve_extension: Whether to preserve file extensions when truncating

    Returns:
        Length-clamped text
    """
    if not text or len(text) <= max_length:
        return text

    if preserve_extension and "." in text:
        name_part: str
        ext_part: str
        name_part, ext_part = split_name_extension(text)
        available_length: int = max_length - len(ext_part)
        if available_length > 10:  # Ensure minimum usable length
            return name_part[:available_length] + ext_part

    return text[:max_length]


def remove_filesystem_unsafe_chars(text: str) -> str:
    """Remove characters that are unsafe for filesystem use.

    Args:
        text: The text to clean

    Returns:
        Text with filesystem-unsafe characters replaced with underscores
    """
    if not text:
        return text

    # Replace Windows/filesystem problematic characters
    return re.sub(r'[<>:"/\\|?*]', "_", text)


def remove_special_characters(text: str, preserve_path_separators: bool = True) -> str:
    """Remove special characters that can cause issues.

    Args:
        text: The text to clean
        preserve_path_separators: Whether to keep / and \\ for paths

    Returns:
        Text with special characters removed
    """
    if not text:
        return text

    # Define special characters to remove
    special_chars = "[](){}#@!&*+=<>|?\"':;,`~"

    # If preserving path separators, don't remove / and \\
    if not preserve_path_separators:
        special_chars += "/\\"

    # Remove each special character
    cleaned: str = text
    for char in special_chars:
        cleaned = cleaned.replace(char, "")

    return cleaned


def normalize_whitespace_and_underscores(text: str) -> str:
    """Normalize multiple spaces/underscores to single underscore.

    Args:
        text: The text to normalize

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return text

    # Replace multiple spaces/underscores with single underscore
    text = re.sub(r"[\s_]+", "_", text)
    return text


def strip_leading_trailing_chars(text: str, chars: str = "._") -> str:
    """Strip specific characters from start and end of text.

    Args:
        text: The text to strip
        chars: Characters to strip (default: '._')

    Returns:
        Stripped text
    """
    if not text:
        return text
    return text.strip(chars)


def ensure_non_empty(text: str, default: str = "file") -> str:
    """Ensure text is not empty, returning default if it is.

    Args:
        text: The text to check
        default: Default value if text is empty

    Returns:
        Original text or default
    """
    if not text or not text.strip():
        return default
    return text


def split_name_extension(filename: str) -> tuple[str, str]:
    """Split filename into name and extension parts.

    Args:
        filename: The filename to split

    Returns:
        Tuple of (name, extension_with_dot)
    """
    if not filename:
        return ("", "")

    # Find last dot
    last_dot = filename.rfind(".")
    if last_dot <= 0:  # No dot, or dot at start (hidden file)
        return (filename, "")

    return (filename[:last_dot], filename[last_dot:])


def remove_emojis_and_symbols(text: str) -> str:
    """Remove emoji and symbol unicode characters.

    Args:
        text: The text to clean

    Returns:
        Text with emojis and symbols removed
    """
    if not text:
        return text

    # Remove characters in Symbol and Other categories
    cleaned = []
    for char in text:
        cat = unicodedata.category(char)
        # Keep letters, marks, numbers, punctuation, separators
        # Remove symbols (S*) and other (C*) except format (Cf)
        if not cat.startswith("S") and not (cat.startswith("C") and cat != "Cf"):
            cleaned.append(char)

    return "".join(cleaned)


def remove_non_ascii_chars(text: str) -> str:
    """Remove non-ASCII characters from text.

    Args:
        text: The text to clean

    Returns:
        Text with only ASCII characters
    """
    if not text:
        return text

    return text.encode("ascii", errors="ignore").decode("ascii")


def convert_fullwidth_to_ascii(text: str) -> str:
    """Convert fullwidth characters to ASCII equivalents.

    Args:
        text: The text to convert

    Returns:
        Text with fullwidth chars converted to ASCII
    """
    if not text:
        return text

    # NFKC normalization converts fullwidth to ASCII
    return unicodedata.normalize("NFKC", text)


def remove_multiple_periods(text: str) -> str:
    """Replace multiple consecutive periods with single period.

    Args:
        text: The text to clean

    Returns:
        Text with single periods
    """
    if not text:
        return text

    return re.sub(r"\.{2,}", ".", text)


def remove_ytdlp_format_codes(text: str) -> str:
    """Remove yt-dlp format codes like [1080p], [f137+f251], .f251, etc.

    Args:
        text: The text to clean

    Returns:
        Text with format codes removed
    """
    if not text:
        return text

    # Remove common yt-dlp format patterns in brackets
    patterns = [
        r"\[f\d+\+?f?\d*\]",  # [f137+f251], [f140]
        r"\[\d{3,4}p\]",  # [1080p], [720p]
        r"\[NA\]",  # [NA]
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Remove format codes at the end (like .f251, .f140, etc.)
    cleaned = re.sub(r"\.f\d+$", "", cleaned)
    # Remove format codes in the middle
    cleaned = re.sub(r"\.f\d+\.", ".", cleaned)

    return cleaned


def sanitize_reserved_names(text: str) -> str:
    """Handle Windows reserved filenames (CON, PRN, AUX, etc.).

    Args:
        text: The filename to check

    Returns:
        Safe filename (prefixed with _ if reserved)
    """
    if not text:
        return text

    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }

    name_upper = text.upper().split(".")[0]
    if name_upper in reserved:
        return "_" + text

    return text


def validate_path_safety(path: str) -> bool:
    """Validate that a path is safe to use (no directory traversal, etc.).

    Args:
        path: Path to validate

    Returns:
        True if path is safe, False otherwise
    """
    if not path:
        return False

    # Check for directory traversal attempts
    if ".." in path or path.startswith("/") or ":" in path[1:]:
        return False

    # Check for problematic characters
    problematic_chars = ["<", ">", ":", '"', "|", "?", "*"]
    if any(char in path for char in problematic_chars):
        return False

    return True


def convert_to_ascii_only(text: str) -> str:
    """Convert text to ASCII-only characters using Unicode normalization.

    Args:
        text: The text to convert

    Returns:
        ASCII-only text
    """
    if not text:
        return text

    # Normalize and convert to ASCII
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


# Maximum length for a tag (handles most proper names, compound words, etc.)
MAX_TAG_LENGTH = 60


def sanitize_tag(tag: str, max_length: int = MAX_TAG_LENGTH) -> str | None:
    """Sanitize a tag string for safe storage and display.

    Designed for image tagging workflows where LLM output may contain
    unexpected characters, escape sequences, or formatting artifacts.

    Allowed characters:
    - ASCII letters (a-z, A-Z)
    - Digits (0-9)
    - Common punctuation: space, hyphen, apostrophe, ampersand, period, comma
    - Parentheses for disambiguation: ()

    Args:
        tag: Raw tag string from LLM or other source.
        max_length: Maximum allowed length (default 60).

    Returns:
        Sanitized tag string, or None if tag is invalid/empty after cleaning.

    Examples:
        >>> sanitize_tag("Blue Cat")
        'Blue Cat'
        >>> sanitize_tag("Arc de Triomphe")
        'Arc de Triomphe'
        >>> sanitize_tag("O'Reilly")
        "O'Reilly"
        >>> sanitize_tag("R&B")
        'R&B'
        >>> sanitize_tag("```json\\n")
        None
        >>> sanitize_tag("a]$%^*weird[tag")
        'aweirdtag'
    """
    if not tag:
        return None

    # Strip leading/trailing whitespace
    tag = tag.strip()

    if not tag:
        return None

    # Normalize Unicode (convert é → e, etc.)
    tag = unicodedata.normalize("NFKD", tag)

    # Remove control characters and non-printable chars
    tag = "".join(c for c in tag if unicodedata.category(c)[0] != "C")

    # Define allowed characters: letters, digits, space, hyphen, apostrophe,
    # ampersand, period, comma, parentheses
    allowed_pattern = re.compile(r"[^a-zA-Z0-9 \-'&.,()]")
    tag = allowed_pattern.sub("", tag)

    # Collapse multiple spaces
    tag = re.sub(r"\s+", " ", tag)

    # Strip again after substitutions
    tag = tag.strip()

    # Remove leading/trailing punctuation (except letters/digits)
    tag = tag.strip("-'&.,() ")

    # Enforce max length
    if len(tag) > max_length:
        tag = tag[:max_length].rstrip("-'&.,() ")

    # Reject if too short or just punctuation/digits
    if len(tag) < 2:
        return None

    # Reject if no letters at all (just numbers/punctuation)
    if not any(c.isalpha() for c in tag):
        return None

    return tag


def sanitize_tags(tags: list[str], max_length: int = MAX_TAG_LENGTH) -> list[str]:
    """Sanitize a list of tags, removing invalid ones.

    Args:
        tags: List of raw tag strings.
        max_length: Maximum allowed length per tag.

    Returns:
        List of valid, sanitized tags (empty/invalid tags removed).
    """
    result = []
    for tag in tags:
        sanitized = sanitize_tag(tag, max_length)
        if sanitized:
            result.append(sanitized)
    return result
