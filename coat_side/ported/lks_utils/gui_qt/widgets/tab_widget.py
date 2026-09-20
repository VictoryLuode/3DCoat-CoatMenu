"""TabWidget - A styled tab widget for organizing content into tabs.

Provides dark theme styling matching Qt panel aesthetics.
"""
from __future__ import annotations

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# Default tab widget styling for dark theme
DEFAULT_TAB_STYLE: str = """
    QTabWidget::pane {
        border: 1px solid #444;
        background: #2d2d2d;
    }
    QTabBar::tab {
        background: #353535;
        border: 1px solid #444;
        border-bottom: none;
        padding: 6px 10px 6px 8px;
        margin-right: 2px;
        color: #bbb;
        font-size: 11px;
        icon-size: 14px;
    }
    QTabBar::tab:selected {
        background: #2d2d2d;
        color: #90caf9;
        border-bottom: 2px solid #90caf9;
    }
    QTabBar::tab:hover {
        background: #404040;
        color: #fff;
    }
"""


class QTabWidget2(QWidget):
    """A styled tab widget for organizing content into tabs.

    Features:
    - Dark theme styling matching Qt panels
    - Tab bar with horizontal tabs
    - Emoji support in tab labels
    - Scroll area in each tab content

    Signals:
        tab_changed(int): Emitted when current tab changes

    Args:
        parent: Parent widget

    Example:
        tabs = QTabWidget2(parent)
        layout1 = tabs.add_scrollable_tab("📋 General")
        layout1.addWidget(QLabel("General settings here"))

        layout2 = tabs.add_scrollable_tab("⚙️ Advanced")
        layout2.addWidget(QLabel("Advanced settings here"))
    """

    tab_changed = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize tab widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create tab widget with dark styling
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(DEFAULT_TAB_STYLE)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tab_widget)

    def add_tab(self, label: str, widget: QWidget) -> int:
        """Add a tab with a widget.

        Args:
            label: Tab label
            widget: Widget to display in tab

        Returns:
            Index of added tab
        """
        return self._tab_widget.addTab(widget, label)

    def add_scrollable_tab(self, label: str) -> QVBoxLayout:
        """Add a tab with a scrollable content area.

        Args:
            label: Tab label

        Returns:
            QVBoxLayout to add content to

        Example:
            layout = tabs.add_scrollable_tab("Settings")
            layout.addWidget(my_widget)
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(4)

        scroll.setWidget(container)
        self._tab_widget.addTab(scroll, label)

        return content_layout

    def insert_tab(self, index: int, label: str, widget: QWidget) -> int:
        """Insert a tab at specific index.

        Args:
            index: Position to insert
            label: Tab label
            widget: Widget to display

        Returns:
            Index of inserted tab
        """
        return self._tab_widget.insertTab(index, widget, label)

    def remove_tab(self, index: int) -> None:
        """Remove a tab by index.

        Args:
            index: Tab index to remove
        """
        self._tab_widget.removeTab(index)

    def current_index(self) -> int:
        """Get current tab index."""
        return self._tab_widget.currentIndex()

    def set_current_index(self, index: int) -> None:
        """Set current tab by index.

        Args:
            index: Tab index to activate
        """
        self._tab_widget.setCurrentIndex(index)

    def tab_count(self) -> int:
        """Get number of tabs."""
        return self._tab_widget.count()

    def set_tab_text(self, index: int, text: str) -> None:
        """Set tab label text.

        Args:
            index: Tab index
            text: New label text
        """
        self._tab_widget.setTabText(index, text)

    def set_tab_icon(self, index: int, icon: QIcon) -> None:
        """Set the icon for a tab.

        Args:
            index: Tab index
            icon: QIcon to display left of the label
        """
        self._tab_widget.setTabIcon(index, icon)

    def tab_text(self, index: int) -> str:
        """Get tab label text.

        Args:
            index: Tab index

        Returns:
            Tab label text
        """
        return self._tab_widget.tabText(index)

    def set_tab_enabled(self, index: int, enabled: bool) -> None:
        """Enable or disable a tab.

        Args:
            index: Tab index
            enabled: Whether to enable
        """
        self._tab_widget.setTabEnabled(index, enabled)

    def is_tab_enabled(self, index: int) -> bool:
        """Check if tab is enabled.

        Args:
            index: Tab index

        Returns:
            True if enabled
        """
        return self._tab_widget.isTabEnabled(index)

    def widget(self, index: int) -> QWidget | None:
        """Get widget at tab index.

        Args:
            index: Tab index

        Returns:
            Widget or None
        """
        return self._tab_widget.widget(index)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change event.

        Args:
            index: New tab index
        """
        self.tab_changed.emit(index)
