"""
LKS UI Widgets - DEPRECATED: Import from ported.utils.ui.widgets package instead.

This file is kept for backwards compatibility. All widgets have been moved to
individual files in ported.utils/ui/widgets/ for better maintainability.

New location:
    from ported.utils.ui.widgets import CollapsibleSection, ButtonGrid, ActivityLog
    from ported.utils.ui.widgets import ToolTip, add_tooltip  # New!

Individual widget files:
    - ported.utils/ui/widgets/collapsible_section.py
    - ported.utils/ui/widgets/button_grid.py
    - ported.utils/ui/widgets/activity_log.py
    - ported.utils/ui/widgets/labeled_slider.py
    - ported.utils/ui/widgets/section_header.py
    - ported.utils/ui/widgets/tab_widget.py
    - ported.utils/ui/widgets/tooltip.py
"""
from __future__ import annotations

# Re-export everything from the new widgets package for backwards compatibility
from ported.utils.ui.widgets import (
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
