"""HTMLFileResource — HTML content loaded from .html files."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ported.utils.ui.widgets.text_resource import _resolve_path


@dataclass
class HTMLFileResource:
    """HTML content loaded from an external .html file.

    Rendered by MarkdownDisplay via QTextBrowser.setHtml().
    Tooltips pass HTML through to widget.setToolTip() directly (Qt tooltips
    support a limited HTML subset: <b>, <i>, <br>, <span style="color:...">).
    .html files preview correctly in code editors.
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
