"""MarkdownFileResource — markdown content loaded from .md files."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ported.utils.ui.widgets.text_resource import _resolve_path


@dataclass
class MarkdownFileResource:
    """Markdown / HTML content loaded from an external .md file.

    Rendered by MarkdownDisplay via QTextBrowser.setMarkdown().
    For tooltips, ``add_tooltip`` converts markdown to Qt-safe HTML, or passes
    through HTML-authored tooltips (``<p>…</p>``) unchanged — the project
    convention for rich tooltips.
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
