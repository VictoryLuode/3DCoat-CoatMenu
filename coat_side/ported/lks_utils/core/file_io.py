"""
Simple file I/O utilities: atomic writes and stable short hashes.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ported.lks_utils.core.transient_file_io import hold_and_retry_io
from ported.lks_utils.text.filename import sanitize_filename
from ported.lks_utils.text.sanitization import clamp_length

# Encoding constants
DEFAULT_ENCODING: str = "utf-8"
UTF8_BOM_ENCODING: str = "utf-8-sig"

# Hash configuration
DEFAULT_HASH_LENGTH: int = 10


def atomic_write(path: str, data: str | bytes, *, encoding: str = DEFAULT_ENCODING) -> None:
    """Write data atomically by writing to a temp file in the same dir then replacing.

    Works for text and bytes. Creates parent directory if needed.

    Args:
        path: Destination file path
        data: Content to write (str or bytes)
        encoding: Encoding for string data (default: utf-8)

    Notes:
        - Always writes bytes to avoid platform default encodings (e.g., cp1252 on Windows).
          If a string is provided, it is encoded using the provided encoding (default UTF-8).
        - On Windows, concurrent readers/writers (MCP mutations, workbench live reload,
          antivirus) can briefly lock targets. Transient lock errors retry via
          :func:`hold_and_retry_io` before surfacing failure.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, str):
        payload: bytes = data.encode(encoding)
    elif isinstance(data, bytearray):
        payload = bytes(data)
    else:
        payload = data

    def _write_once() -> None:
        fd_prefix: str = p.name + "."
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(p.parent),
            prefix=fd_prefix,
            suffix=".tmp",
        ) as tmp:
            tmp_path: Path = Path(tmp.name)
            tmp.write(payload)
        try:
            if p.exists():
                try:
                    p.chmod(0o644)
                except OSError:
                    pass
            os.replace(str(tmp_path), str(p))
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    hold_and_retry_io(_write_once)


def _normalize_for_hash(obj: Any) -> Any:
    """Normalize object for consistent hashing (sort dict keys recursively)."""
    if isinstance(obj, dict):
        return {k: _normalize_for_hash(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_hash(x) for x in obj]
    return obj


def hash_from_config(obj: Any, length: int = DEFAULT_HASH_LENGTH) -> str:
    """Stable short hex hash of a JSON-serializable object.

    Args:
        obj: Any JSON-serializable object
        length: Number of hex characters to return (default: 10)

    Returns:
        First `length` hex chars of sha1 hash

    Notes:
        - Sorts dict keys recursively for stability
        - Uses compact JSON serialization
    """
    norm: Any = _normalize_for_hash(obj)
    s: str = json.dumps(norm, separators=(",", ":"), ensure_ascii=False)
    h: str = hashlib.sha1(s.encode(DEFAULT_ENCODING)).hexdigest()
    return h[: max(1, int(length))]


def ensure_directory_exists(path: str) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object for the directory
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def md5_bytes(data: bytes) -> str:
    """Hex MD5 digest for bytes."""
    return hashlib.md5(data).hexdigest()


def md5_file(path: str | Path) -> str:
    """Hex MD5 digest for a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str, max_length: int = 200) -> str:
    """Create a safe filename from arbitrary string.

    Args:
        name: Input string
        max_length: Maximum filename length

    Returns:
        Safe filename string
    """
    safe = sanitize_filename(name)
    return clamp_length(safe, max_length, preserve_extension=True)
