"""ToolTip / add_tooltip — re-exported from ported.lks_utils with file resource support."""
from __future__ import annotations

import re

from ported.lks_utils.gui_qt.widgets.tooltip import add_tooltip as _lks_add_tooltip
from PySide6.QtWidgets import QWidget

from ported.utils.ui.widgets.html_file_resource import HTMLFileResource
from ported.utils.ui.widgets.markdown_file_resource import MarkdownFileResource
from ported.utils.ui.widgets.text_resource import TextFileResource

# COLOR_ACCENT_ALT from ported.utils/ui/styles.py — kept local to avoid coat import chain.
_TOOLTIP_ACCENT: str = "#ffb74d"


def _markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML for Qt tooltip display.

    Qt tooltips support a limited HTML subset: <b>, <i>, <br>, <span style="...">.
    Bold text gets the theme accent color for visual emphasis.

    Already-HTML content (tooltips authored as ``<p>…</p>``) is returned as-is
    so Qt always treats it as rich text. Markdown is joined with ``<br>`` only —
    never bare newlines — so ``<br>`` cannot appear as literal plain text.
    """
    stripped_all: str = text.strip()
    # Pass through HTML-authored tooltips (project convention for Qt tooltips).
    if stripped_all.startswith("<") and (
        "</p>" in stripped_all or "<br" in stripped_all.lower()
    ):
        return stripped_all

    paragraphs: list[str] = []
    current: list[str] = []

    def _flush() -> None:
        if current:
            paragraphs.append("<br>".join(current))
            current.clear()

    for line in text.split("\n"):
        stripped: str = line.strip()
        if not stripped or re.match(r"^[-*_]{3,}$", stripped):
            _flush()
            continue
        # Headings
        if re.match(r"^#{1,6}\s", stripped):
            heading_text: str = re.sub(r"^#{1,6}\s+", "", stripped)
            current.append(f"<b>{heading_text}</b>")
            continue
        # Inline formatting: bold first (with highlight), then italic
        line_html: str = re.sub(
            r"\*\*(.+?)\*\*",
            rf'<b style="color:{_TOOLTIP_ACCENT};">\1</b>',
            stripped,
        )
        line_html = re.sub(r"\*(.+?)\*", r"<i>\1</i>", line_html)
        # Code
        line_html = re.sub(r"`(.+?)`", r"<code>\1</code>", line_html)
        # Links
        line_html = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", line_html)
        # List items
        if re.match(r"^[\s]*[-*+]\s", stripped):
            line_html = re.sub(r"^[\s]*[-*+]", "•", line_html)
        current.append(line_html)

    _flush()
    html: str = "<br><br>".join(paragraphs)
    # Wrap so Qt rich-text detection always engages (must start with '<').
    if html and not html.startswith("<"):
        html = f"<p>{html}</p>"
    return html


def add_tooltip(widget: QWidget, content: str | TextFileResource | MarkdownFileResource | HTMLFileResource) -> None:
    """Attach a tooltip to a widget.

    Supports plain strings and file-based resources:
    - HTMLFileResource → text passes through directly (Qt tooltips support <b>, <i>, <br>, <span>)
    - MarkdownFileResource → markdown converted to styled HTML
    - TextFileResource → used as-is
    - str → used directly
    """
    if isinstance(content, HTMLFileResource):
        widget.setToolTip(content.text)
    elif isinstance(content, MarkdownFileResource):
        widget.setToolTip(_markdown_to_html(content.text))
    elif isinstance(content, TextFileResource):
        widget.setToolTip(content.text)
    else:
        widget.setToolTip(content)


class ToolTip:
    """Backward-compatible ToolTip class.

    New code should prefer ``add_tooltip(widget, content)``.
    This class is kept for backward compatibility.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        show_delay: int = 500,
        hide_delay: int = 100,
        max_width: int = 300,
        style: str | None = None,
    ) -> None:
        self._text: str = text
        self._attached: list[QWidget] = []

    @classmethod
    def from_resource(cls, resource: TextFileResource | MarkdownFileResource | HTMLFileResource) -> ToolTip:
        """Create a ToolTip from a file resource."""
        if isinstance(resource, MarkdownFileResource):
            text = _markdown_to_html(resource.text)
        else:
            text = resource.text
        return cls(text=text)

    def set_text(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def set_show_delay(self, delay: int) -> None:
        pass

    def set_hide_delay(self, delay: int) -> None:
        pass

    def set_max_width(self, width: int) -> None:
        pass

    def set_style(self, style: str) -> None:
        pass

    def attach(self, widget: QWidget) -> None:
        if widget not in self._attached:
            widget.setToolTip(self._text)
            self._attached.append(widget)

    def detach(self, widget: QWidget) -> None:
        if widget in self._attached:
            self._attached.remove(widget)

    def show_at(self, position) -> None:
        pass

    def show_now(self, position=None) -> None:
        pass

    def hide_delayed(self) -> None:
        pass

    def hide_now(self) -> None:
        pass


__all__ = ["ToolTip", "add_tooltip"]
