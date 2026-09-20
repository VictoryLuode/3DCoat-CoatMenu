"""Text resource types for file-based content loading."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Cache the LKS root once
_LKS_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_path(path_str: str, base_dir: Path | str | None = None) -> Path:
    """Resolve a relative path against base_dir or LKS root data/."""
    path = Path(path_str)
    if path.is_absolute():
        return path
    if base_dir is not None:
        base = Path(base_dir) if not isinstance(base_dir, Path) else base_dir
        if base.is_file():
            base = base.parent
        return (base / path).resolve()
    # Default: resolve relative to LKS root data/
    return (_LKS_ROOT / "data" / path).resolve()


@dataclass
class TextFileResource:
    """Raw text content loaded from an external file.

    No formatting is applied. Use for plain text that should display as-is.
    """

    path: str
    base_dir: Path | str | None = None
    _cached_text: str | None = field(default=None, repr=False, init=False)

    @property
    def text(self) -> str:
        if self._cached_text is None:
            self._cached_text = _resolve_path(self.path, self.base_dir).read_text(encoding="utf-8")
        return self._cached_text

    @property
    def resolved_path(self) -> Path:
        return _resolve_path(self.path, self.base_dir)

    def invalidate(self) -> None:
        self._cached_text = None


# Backward compatibility alias
TextResource = TextFileResource
