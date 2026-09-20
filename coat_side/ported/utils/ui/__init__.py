"""
LKS UI module.

Contains PySide6/Qt-based UI components and styles for the LKS cModule.

Widgets (imported from ported.utils.ui.widgets package):
    CollapsibleSection: Expandable/collapsible group with header
    ButtonGrid: Grid of buttons with scope-based layout
    ActivityLog: Scrollable log display with timestamped messages
    LabeledSlider: Slider with label and value display
    SectionHeader: Styled section header label
    TabWidget: Tabbed container for organizing content
    ToolTip: Rich text tooltip with delayed display
    add_tooltip: Utility to add tooltips to widgets

Individual widget files are in ported.utils/ui/widgets/ for better maintainability.
"""
from .styles import DARK_STYLESHEET
from .widgets import (
    CollapsibleSection,
    ButtonGrid,
    ActivityLog,
    LabeledSlider,
    SectionHeader,
    TabWidget,
    ToolTip,
    add_tooltip,
    LOG_COLORS,
    LOG_PREFIXES,
    HAS_QT,
)

__all__ = [
    "DARK_STYLESHEET",
    "CollapsibleSection",
    "ButtonGrid",
    "ActivityLog",
    "LabeledSlider",
    "SectionHeader",
    "TabWidget",
    "ToolTip",
    "add_tooltip",
    "LOG_COLORS",
    "LOG_PREFIXES",
    "HAS_QT",
]
