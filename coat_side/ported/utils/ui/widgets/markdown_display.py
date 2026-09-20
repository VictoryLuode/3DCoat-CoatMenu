"""MarkdownDisplay — read-only QTextBrowser for markdown or plain text in dark theme."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

try:
    from PySide6.QtWidgets import QTextBrowser, QSizePolicy, QFrame
    from PySide6.QtCore import Qt

    from ported.utils.ui.widgets.text_resource import TextFileResource
    from ported.utils.ui.widgets.markdown_file_resource import MarkdownFileResource
    from ported.utils.ui.widgets.html_file_resource import HTMLFileResource
    from ported.utils.ui.styles import COLOR_BG_PRIMARY, COLOR_BG_SECONDARY, COLOR_TEXT_PRIMARY, COLOR_BORDER
    HAS_QT: bool = True
except ImportError:
    HAS_QT = False


_DARK_STYLESHEET: str = """
QTextBrowser {{
    background-color: {bg};
    color: {text};
    border: {border_style};
    font-size: 13px;
    padding: 8px;
}}
QTextBrowser:focus {{
    border: 1px solid #90caf9;
}}
QScrollBar:vertical {{
    background: {bg_secondary};
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #555;
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
""".format(
    bg=COLOR_BG_PRIMARY,
    bg_secondary=COLOR_BG_SECONDARY,
    text=COLOR_TEXT_PRIMARY,
    border_style="1px solid " + COLOR_BORDER,
)


class MarkdownDisplay(QTextBrowser):
    """Read-only text browser that renders markdown, HTML, or plain text.

    Features:
        - Auto-detects content type from resource class
        - Auto-scrollbar (appears when content exceeds visible area)
        - Dark theme styling
        - No-frame mode for seamless embedding
        - Min-lines height behavior

    Usage:
        # From a MarkdownFileResource
        display = MarkdownDisplay(MarkdownFileResource("docs/welcome.md"))
        layout.addWidget(display)

        # From an inline string (assumed markdown)
        display = MarkdownDisplay("## Hello\\n\\nThis is **markdown**.")
        layout.addWidget(display)

        # Compact no-frame mode
        display = MarkdownDisplay(resource)
        display.set_compact(True)
    """

    def __init__(
        self,
        content: str | TextFileResource | MarkdownFileResource | HTMLFileResource | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setStyleSheet(_DARK_STYLESHEET)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

        self._min_lines: int = 0

        if content is not None:
            self.set_content(content)

    def set_content(self, content: str | TextFileResource | MarkdownFileResource | HTMLFileResource) -> None:
        """Set the display content from a string or file resource.

        Uses duck-typing (file extension from .path attribute) rather than
        isinstance checks so that the method survives Python module reloads
        where class identity changes across importlib.reload() boundaries.
        """
        if isinstance(content, str):
            self.setMarkdown(content)
        elif hasattr(content, "text"):
            text: str = content.text
            path: str = str(getattr(content, "path", ""))
            path_lower: str = path.lower()
            if path_lower.endswith((".html", ".htm")):
                self.setHtml(text)
            elif path_lower.endswith(".txt"):
                self.setPlainText(text)
            else:
                self.setMarkdown(text)  # default: .md or unknown
        else:
            self.setMarkdown(str(content))

        self._update_height()

    def set_compact(self, compact: bool = True) -> None:
        """Enable/disable compact no-frame mode for seamless embedding."""
        if compact:
            self.setFrameShape(QFrame.Shape.NoFrame)
            self.setStyleSheet(_DARK_STYLESHEET.replace(
                "border: 1px solid " + COLOR_BORDER + ";",
                "border: none;",
            ))
        else:
            self.setFrameShape(QFrame.Shape.StyledPanel)
            self.setStyleSheet(_DARK_STYLESHEET)

    def set_min_lines(self, lines: int) -> None:
        """Set minimum visible lines before scrollbar kicks in."""
        self._min_lines = lines
        self._update_height()

    def _update_height(self) -> None:
        """Adjust height based on content and min_lines setting."""
        if self._min_lines <= 0:
            return
        font_metrics = self.fontMetrics()
        line_height = font_metrics.lineSpacing()
        doc = self.document()
        doc_height = int(doc.size().height())
        min_height = line_height * self._min_lines + 16
        if doc_height < min_height:
            self.setFixedHeight(min_height)
        else:
            self.setMinimumHeight(min_height)
            self.setMaximumHeight(16777215)


if not HAS_QT:
    class MarkdownDisplay:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass
