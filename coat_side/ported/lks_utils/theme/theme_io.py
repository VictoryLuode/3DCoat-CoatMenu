"""JSON I/O for ``Theme`` objects.

Uses ``ported.lks_utils.core.atomic_write`` for safe saves.  Schema versioning:
``{"schema_version": 1, "theme": {...}}``.  Unknown fields on load are
silently ignored for forward compatibility.
"""
from __future__ import annotations

import json
from pathlib import Path

from ported.lks_utils.core import atomic_write
from ported.lks_utils.theme.theme import Theme

_DATA_DIR = Path(__file__).parent / "data"


def save_theme(theme: Theme, path: Path) -> None:
    """Write *theme* to *path* atomically (via a ``.tmp`` sibling)."""
    payload = json.dumps(theme.to_dict(), indent=2, ensure_ascii=False)
    atomic_write(str(path), payload)


def load_theme(path: Path) -> Theme:
    """Load a ``Theme`` from *path*.

    Raises ``ValueError`` with the file path in the message on JSON / schema
    parse failure.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
        raw = json.loads(text)
        return Theme.from_dict(raw)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Failed to load theme from {path}: {exc}") from exc


def load_theme_dir(directory: Path) -> list[Theme]:
    """Load all ``.json`` files from *directory*, sorted by theme name.

    Non-JSON files are silently skipped.  A malformed JSON file raises
    ``ValueError`` with the file path in the message.
    """
    themes: list[Theme] = []
    for json_path in sorted(Path(directory).iterdir()):
        if json_path.suffix.lower() != ".json":
            continue
        themes.append(load_theme(json_path))
    themes.sort(key=lambda t: t.name)
    return themes


def load_builtin_themes() -> list[Theme]:
    """Load the three shipped built-in themes (dark, light, high_contrast)."""
    return load_theme_dir(_DATA_DIR)


def builtin_themes() -> list[Theme]:
    """Public alias for ``load_builtin_themes()``."""
    return load_builtin_themes()


__all__ = ["save_theme", "load_theme", "load_theme_dir",
           "load_builtin_themes", "builtin_themes"]
