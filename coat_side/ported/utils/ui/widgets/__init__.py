"""
LKS UI Widgets Package - Reusable PySide6/Qt components for LKS panels.

This package provides reusable widget primitives for building LKS UI.
Most widgets are now thin re-exports from ported.lks_utils:

- CollapsibleSection: Expandable/collapsible group with header (→ QCollapsibleSection)
- ButtonGrid: Grid of buttons with scope-based layout (→ QButtonGrid)
- ActivityLog: Scrollable log display with timestamped messages (→ QActivityLog)
- LabeledSlider: Slider with label and value display (→ QLabeledSlider)
- SectionHeader: Styled section header label (→ QSectionHeader)
- TabWidget: Tabbed container for organizing content (→ QTabWidget2)
- ToolTip: Rich text tooltip with delayed display (→ simplified compat)
- add_tooltip: Utility function for adding tooltips (→ ported.lks_utils add_tooltip)
- GripBox: Wrap widget with drag column (→ QGripBoxItem)
- GripBoxContainer: Reorderable vertical container with grip columns (→ QGripBoxContainer)
- SideRibbon: Collapsible side ribbon (→ QCollapsiblePanel)
- SvgIcon/SvgIconButton/get_icon: SVG icon widgets (self-contained, uses ported.lks_utils helpers)
- GridRowTable: QGridLayout wrapper with auto column-width normalization (→ QGridRowTable)
- QBadgeButton / make_badge_button: Badge counter buttons (self-contained)
- InfoButton / InfoButtonCompact / InfoPopup: Circular ? button with floating help popup (→ QInfoButton / QInfoButtonCompact)
- TextFileResource: Raw text loaded from external files (self-contained)
- MarkdownFileResource: Markdown content loaded from .md files (self-contained)
- HTMLFileResource: HTML content loaded from .html files (self-contained)
- MarkdownDisplay: Read-only QTextBrowser for markdown/HTML/plain text (self-contained)

Usage:
    from ported.utils.ui.widgets import (
        CollapsibleSection, ButtonGrid, ActivityLog, GripBoxContainer, 
        SideRibbon, Side, SvgIcon, SvgIconButton, get_icon,
        MarkdownDisplay, MarkdownFileResource, HTMLFileResource,
    )

    # Markdown display
    resource = MarkdownFileResource("embedded_docs/guide/welcome.md")
    display = MarkdownDisplay(resource)
    layout.addWidget(display)

    # Tooltip with HTML
    tip = HTMLFileResource("data/tooltips/my_tool.html", base_dir=__file__)
    add_tooltip(button, tip)

    log = ActivityLog(parent)
    log.log_info("Operation complete")
    log.log_error("Something failed")

    # Reorderable sections
    container = GripBoxContainer()
    container.add_widget(section1, "section1")
    container.add_widget(section2, "section2")

    # Side ribbon (now backed by QCollapsiblePanel)
    ribbon = SideRibbon(
        edge=Side.LEFT,
        label="Outliner",
        content_factory=lambda: create_outliner_widget(),
    )

All widgets are re-exported here for backwards compatibility.
"""
from __future__ import annotations

from .collapsible_section import CollapsibleSection
from .button_grid import ButtonGrid
from .activity_log import ActivityLog, LOG_COLORS, LOG_PREFIXES
from .labeled_slider import LabeledSlider
from .section_header import SectionHeader
from .tab_widget import TabWidget
from .tooltip import ToolTip, add_tooltip
from .text_resource import TextFileResource
from .markdown_file_resource import MarkdownFileResource
from .html_file_resource import HTMLFileResource
from .markdown_display import MarkdownDisplay
from .tab_container import TabContainer, StandardTabBody, create_tab_with_revert
from .grip_box_container import GripBoxContainer
from .grip_box_item import GripBox
from .radial_menu import RadialMenuWidget, RadialMenuItem
from .radial_menu_manager import get_manager
from .dwell_progress_node import DwellProgressNode
from .save_load_library import SaveLoadLibrary
from .help_menu import HelpMenu
from .side_ribbon import SideRibbon, Side
from .svg_icon import SvgIcon, SvgIconButton, get_icon, QSquareIconButton
from .scope_button_row import ScopeButtonRow
from .enhanced_slider import EnhancedSlider, QEnhancedSlider
from .grid_row_table import GridRowTable, Align
from .badge_button import QBadgeButton, make_badge_button
from .info_button import InfoButton, InfoButtonCompact, InfoPopup

# Check if Qt is available (re-export for convenience)
try:
    from PySide6.QtWidgets import QWidget
    HAS_QT: bool = True
except ImportError:
    HAS_QT = False

__all__ = [
    "CollapsibleSection",
    "ButtonGrid",
    "ActivityLog",
    "LabeledSlider",
    "SectionHeader",
    "TabWidget",
    "ToolTip",
    "add_tooltip",
    "TabContainer",
    "StandardTabBody",
    "create_tab_with_revert",
    "GripBoxContainer",
    "GripBox",
    "RadialMenuWidget",
    "RadialMenuItem",
    "DwellProgressNode",
    "EnhancedSlider",
    "QEnhancedSlider",
    "SaveLoadLibrary",
    "HelpMenu",
    "SideRibbon",
    "Side",
    "SvgIcon",
    "SvgIconButton",
    "QSquareIconButton",
    "ScopeButtonRow",
    "get_icon",
    "get_manager",
    "GridRowTable",
    "Align",
    "QBadgeButton",
    "make_badge_button",
    "InfoButton",
    "InfoButtonCompact",
    "InfoPopup",
    "TextFileResource",
    "MarkdownFileResource",
    "HTMLFileResource",
    "MarkdownDisplay",
    "LOG_COLORS",
    "LOG_PREFIXES",
    "HAS_QT",
]
