"""
QSvgIconPicker -- drop-down SVG / emoji icon selector with visual preview.

A widget that shows the currently selected icon in a button and opens
a scrollable list popup listing every available SVG file and common
emoji icons so the user can pick one visually.

SVG icons are colored to match the dark theme accent colour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    Qt,
    Signal,
    QByteArray,
    QPoint,
    QSize,
)
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QFont,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QVBoxLayout,
    QScrollArea,
    QSizePolicy,
    QLabel,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
)

# =============================================================================
# DARK THEME COLOUR CONSTANTS
# =============================================================================

_COLOR_BG: str = "#2d2d2d"
_COLOR_BG_BUTTON: str = "#3a3a3a"
_COLOR_BG_BUTTON_HOVER: str = "#4a4a4a"
_COLOR_BG_ITEM_HOVER: str = "#3d3d3d"
_COLOR_BG_ITEM_SELECTED: str = "#264f78"
_COLOR_ACCENT: str = "#90caf9"
_COLOR_TEXT: str = "#ddd"
_COLOR_TEXT_MUTED: str = "#888"
_COLOR_BORDER: str = "#555555"

# =============================================================================
# COMMON EMOJI ICONS (available alongside SVGs)
# =============================================================================

_EMOJI_ICONS: list[str] = [
    "🔻", "🔺", "🔄", "⚙️", "📐", "📏", "👁️", "👻",
    "🎨", "✨", "🔧", "📦", "🗂️", "🌳", "☝️", "🌎",
    "✂️", "🔗", "🎯", "💾", "📁", "🖌️", "🔍", "⬆️", "⬇️",
    "🚫", "💡", "🔥", "❄️", "⭐", "🔒", "🔓", "⚡",
    "🛡️", "🧹", "➕", "➖", "✖️", "↔️", "↕️", "↗️",
]

# Size of the icon preview in list rows
_LIST_ICON_SIZE: int = 20


# =============================================================================
# SVG ICON PICKER
# =============================================================================

class QSvgIconPicker(QWidget):
    """Drop-down picker that renders SVG / emoji icon previews in a list popup.

    Parameters
    ----------
    svg_directory:
        Directory to scan for ``.svg`` files.  ``_template.svg`` is excluded.
    parent:
        Optional parent widget.
    icon_size:
        Size of the preview icon in the *main button* (default 16×16).
    """

    #: Emitted when the selected icon value changes (svg filename, emoji, or "").
    currentValueChanged = Signal(str)

    def __init__(
        self,
        svg_directory: str | Path,
        parent: Optional[QWidget] = None,
        icon_size: int = 16,
        columns: int = 5,   # kept for backward compat, ignored
    ) -> None:
        super().__init__(parent)
        self._svg_dir: Path = Path(svg_directory)
        self._icon_size: int = icon_size
        self._current_path: str = ""
        self._svg_files: list[str] = []
        self._svg_content_cache: dict[str, str] = {}
        self._popup: Optional[QFrame] = None

        self._scan_svgs()
        self._setup_ui()
        self._update_button()

    # ------------------------------------------------------------------
    # SVG discovery
    # ------------------------------------------------------------------

    def _scan_svgs(self) -> None:
        """Discover .svg files in *svg_directory*, excluding ``_template.svg``."""
        if not self._svg_dir.is_dir():
            return
        names: list[str] = sorted(
            p.name for p in self._svg_dir.glob("*.svg")
            if p.name != "_template.svg"
        )
        self._svg_files = names

        # Pre-load content for rendering
        for name in names:
            try:
                content: str = (
                    (self._svg_dir / name).read_text(encoding="utf-8")
                )
                self._svg_content_cache[name] = content
            except Exception:
                pass
        # #region agent log
        try:
            with open(r"c:\BTS_SSD\3DCoat_Userprefs_SSD_2025\MyDocuments\UserPrefs\Scripts\cExtensions\LKS\debug-2b2209.log", "a") as _f:
                import json as _json
                _f.write(_json.dumps({"sessionId":"2b2209","runId":"init","hypothesisId":"B","location":"svg_icon_picker.py:_scan_svgs","message":"SVG scan done","data":{"svg_dir":str(self._svg_dir),"svg_count":len(names),"cache_count":len(self._svg_content_cache)},"timestamp":__import__("time").time()}) + "\n")
        except: pass
        # #endregion

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout: QHBoxLayout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._button: QPushButton = QPushButton()
        self._button.setMinimumHeight(22)
        self._button.setStyleSheet(self._button_style())
        self._button.clicked.connect(self._toggle_popup)
        layout.addWidget(self._button)

    @staticmethod
    def _button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {_COLOR_BG_BUTTON};
                border: 1px solid {_COLOR_BORDER};
                border-radius: 3px;
                color: {_COLOR_TEXT};
                padding: 2px 6px;
                text-align: left;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {_COLOR_BG_BUTTON_HOVER};
            }}
        """

    # ------------------------------------------------------------------
    # Popup
    # ------------------------------------------------------------------

    def _toggle_popup(self) -> None:
        if self._popup and self._popup.isVisible():
            self._popup.close()
            return
        self._show_popup()

    def _show_popup(self) -> None:
        self._popup = QFrame(self)
        # #region agent log
        try:
            with open(r"c:\BTS_SSD\3DCoat_Userprefs_SSD_2025\MyDocuments\UserPrefs\Scripts\cExtensions\LKS\debug-2b2209.log", "a") as _f:
                import json as _json
                _f.write(_json.dumps({"sessionId":"2b2209","runId":"init","hypothesisId":"E","location":"svg_icon_picker.py:_show_popup","message":"popup_opened","data":{"svg_count":len(self._svg_files),"cache_count":len(self._svg_content_cache)},"timestamp":__import__("time").time()}) + "\n")
        except: pass
        # #endregion
        self._popup.setWindowFlags(
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        )
        self._popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._popup.setStyleSheet(f"""
            QFrame {{
                background-color: {_COLOR_BG};
                border: 1px solid {_COLOR_BORDER};
                border-radius: 4px;
            }}
        """)

        popup_layout: QVBoxLayout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(0)

        # List widget
        list_widget: QListWidget = QListWidget()
        list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
            }}
            QListWidget::item {{
                color: {_COLOR_TEXT};
                padding: 2px 4px;
                border-radius: 3px;
            }}
            QListWidget::item:hover {{
                background-color: {_COLOR_BG_ITEM_HOVER};
            }}
            QListWidget::item:selected {{
                background-color: {_COLOR_BG_ITEM_SELECTED};
            }}
        """)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_widget.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background-color: {_COLOR_BG};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #707070;
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #909090;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # "(none)" entry at top
        none_item: QListWidgetItem = QListWidgetItem()
        none_widget: QWidget = self._make_row_widget("", "(none)")
        none_item.setSizeHint(none_widget.sizeHint())
        none_item.setData(Qt.ItemDataRole.UserRole, "")
        list_widget.addItem(none_item)
        list_widget.setItemWidget(none_item, none_widget)

        # --- Emoji section header ---
        emoji_header: QListWidgetItem = self._make_section_header("Emoji Icons")
        list_widget.addItem(emoji_header)

        # Emoji entries
        for emoji in _EMOJI_ICONS:
            emoji_item: QListWidgetItem = QListWidgetItem()
            emoji_widget: QWidget = self._make_row_widget(emoji, emoji)
            emoji_item.setSizeHint(emoji_widget.sizeHint())
            emoji_item.setData(Qt.ItemDataRole.UserRole, emoji)
            list_widget.addItem(emoji_item)
            list_widget.setItemWidget(emoji_item, emoji_widget)

        # --- SVG section header ---
        svg_header: QListWidgetItem = self._make_section_header("SVG Icons")
        list_widget.addItem(svg_header)

        # SVG entries
        for svg_name in self._svg_files:
            display_name: str = svg_name.replace(".svg", "")
            svg_item: QListWidgetItem = QListWidgetItem()
            svg_widget: QWidget = self._make_row_widget(svg_name, display_name)
            svg_item.setSizeHint(svg_widget.sizeHint())
            svg_item.setData(Qt.ItemDataRole.UserRole, svg_name)
            list_widget.addItem(svg_item)
            list_widget.setItemWidget(svg_item, svg_widget)

        list_widget.itemClicked.connect(self._on_list_item_clicked)

        # Size: fixed width, max 12 rows visible
        popup_width: int = 220
        row_height: int = 28
        section_height: int = 22
        max_rows: int = 12
        visible_row_count: int = min(
            max_rows,
            list_widget.count()
        )
        popup_height: int = (
            visible_row_count * row_height + 16
        )
        self._popup.setFixedSize(popup_width, popup_height)

        popup_layout.addWidget(list_widget)

        # Position below button
        global_pos: QPoint = self._button.mapToGlobal(
            QPoint(0, self._button.height())
        )
        self._popup.move(global_pos)
        self._popup.show()

    def _make_section_header(self, text: str) -> QListWidgetItem:
        """Create a non-selectable section header item."""
        item: QListWidgetItem = QListWidgetItem()
        label: QLabel = QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {_COLOR_TEXT_MUTED};
                font-size: 10px;
                font-weight: bold;
                padding: 2px 4px 0px 4px;
            }}
        """)
        item.setSizeHint(QSize(200, 18))
        item.setFlags(Qt.ItemFlag.NoItemFlags)  # not selectable
        return item

    def _make_row_widget(self, value: str, display_name: str) -> QWidget:
        """Create a horizontal row: icon preview + name label."""
        row: QWidget = QWidget()
        row_layout: QHBoxLayout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 1, 4, 1)
        row_layout.setSpacing(6)

        # Icon preview
        icon_label: QLabel = QLabel()
        icon_label.setFixedSize(_LIST_ICON_SIZE, _LIST_ICON_SIZE)

        if value and value in self._svg_content_cache:
            # Render colored SVG
            pixmap: QPixmap = self._colored_svg_pixmap(value, _LIST_ICON_SIZE)
            icon_label.setPixmap(pixmap)
        elif value and len(value) <= 4:
            # Emoji — render as text
            icon_label.setText(value)
            icon_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            icon_label.setStyleSheet(f"font-size: 14px; background: transparent;")
        # else: "(none)" — no icon

        row_layout.addWidget(icon_label)

        # Name label
        name_label: QLabel = QLabel(display_name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {_COLOR_TEXT};
                font-size: 11px;
                background: transparent;
            }}
        """)
        row_layout.addWidget(name_label, stretch=1)

        row.setFixedHeight(24)
        return row

    def _colored_svg_pixmap(self, svg_name: str, size: int) -> QPixmap:
        """Render an SVG file to a QPixmap, replacing ``currentColor`` with the
        dark-theme accent colour."""
        pixmap: QPixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        content: str = self._svg_content_cache.get(svg_name, "")
        if not content:
            return pixmap

        # Replace currentColor with theme accent so SVG is visible on dark bg
        content = content.replace("currentColor", _COLOR_ACCENT)

        renderer: QSvgRenderer = QSvgRenderer(QByteArray(content.encode("utf-8")))
        # #region agent log
        try:
            with open(r"c:\BTS_SSD\3DCoat_Userprefs_SSD_2025\MyDocuments\UserPrefs\Scripts\cExtensions\LKS\debug-2b2209.log", "a") as _f:
                import json as _json
                _f.write(_json.dumps({"sessionId":"2b2209","runId":"init","hypothesisId":"C","location":"svg_icon_picker.py:_colored_svg_pixmap","message":"renderer_check","data":{"svg_name":svg_name,"renderer_valid":renderer.isValid(),"content_len":len(content),"first_80":content[:80]},"timestamp":__import__("time").time()}) + "\n")
        except: pass
        # #endregion
        if not renderer.isValid():
            return pixmap

        painter: QPainter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        return pixmap

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_list_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle list item click — update selection and dismiss popup."""
        value: str = item.data(Qt.ItemDataRole.UserRole) or ""
        if value != self._current_path:
            self._current_path = value
            self._update_button()
            self.currentValueChanged.emit(value)

        if self._popup:
            self._popup.close()
            self._popup = None

    def _update_button(self) -> None:
        """Refresh the main button display."""
        # #region agent log
        _branch: str = "unknown"
        # #endregion
        if self._current_path and self._current_path in self._svg_content_cache:
            # SVG icon — show colored preview
            _branch = "svg_cache_hit"
            pixmap: QPixmap = self._colored_svg_pixmap(
                self._current_path, self._icon_size
            )
            self._button.setIcon(QIcon(pixmap))
            self._button.setIconSize(QSize(self._icon_size, self._icon_size))
            display: str = self._current_path.replace(".svg", "")
        elif self._current_path:
            # Emoji or unrecognised string
            _branch = "no_cache_fallback"
            self._button.setIcon(QIcon())
            display = self._current_path
        else:
            _branch = "empty_path"
            self._button.setIcon(QIcon())
            display = "(none)"

        self._button.setText(display)
        # #region agent log
        try:
            with open(r"c:\BTS_SSD\3DCoat_Userprefs_SSD_2025\MyDocuments\UserPrefs\Scripts\cExtensions\LKS\debug-2b2209.log", "a") as _f:
                import json as _json
                _f.write(_json.dumps({"sessionId":"2b2209","runId":"init","hypothesisId":"A","location":"svg_icon_picker.py:_update_button","message":_branch,"data":{"current_path":self._current_path,"display":display,"in_cache":self._current_path in self._svg_content_cache},"timestamp":__import__("time").time()}) + "\n")
        except: pass
        # #endregion

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def currentSvgPath(self) -> str:
        """Return the currently selected icon value (svg filename, emoji, or ``""``)."""
        return self._current_path

    def setCurrentSvgPath(self, path: str) -> None:
        """Set the selection programmatically.

        *path* may be a bare filename (e.g. ``"decimate.svg"``), an emoji
        character, or empty for ``"(none)"``.
        """
        self._current_path = path
        self._update_button()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._popup and self._popup.isVisible():
            self._popup.close()
            self._popup = None
        super().closeEvent(event)
