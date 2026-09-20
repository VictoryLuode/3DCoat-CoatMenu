"""
Hotkey Editor - UI Styles and Constants

Constants, colors, and Qt stylesheet for the hotkey editor.
"""
from __future__ import annotations

# =============================================================================
# TABLE COLUMN INDICES
# =============================================================================

COL_COMMAND: int = 0
COL_KEY: int = 1
COL_MODIFIERS: int = 2
COL_ROOM: int = 3
COL_STATUS: int = 4
COL_USER_DEF: int = 5
COL_STACKABLE: int = 6

# =============================================================================
# GARBAGE KEY DEFAULTS
# =============================================================================

# Some 3DCoat shortcuts can't be unmapped - they respawn with defaults
# Mapping to a garbage key is the only way to disable them
DEFAULT_GARBAGE_KEY: str = "END"
DEFAULT_GARBAGE_CTRL: bool = True
DEFAULT_GARBAGE_ALT: bool = False
DEFAULT_GARBAGE_SHIFT: bool = False

# =============================================================================
# STATUS COLORS
# =============================================================================

COLOR_DUPLICATE: str = "#ef5350"  # Red
COLOR_CONFLICT: str = "#ffb74d"   # Orange
COLOR_ORPHAN: str = "#ce93d8"     # Purple
COLOR_NORMAL: str = "#e0e0e0"     # Default gray
COLOR_UNASSIGNED: str = "#666666"  # Dim gray
COLOR_GARBAGE: str = "#78909c"    # Blue-gray (intentionally disabled)

# =============================================================================
# STATUS ICONS
# =============================================================================

ICON_DUPLICATE: str = "⊗"  # Duplicate
ICON_CONFLICT: str = "⚡"   # Conflict
ICON_ORPHAN: str = "?"     # Orphan room
ICON_GARBAGE: str = "🗑️"   # Garbage key (soft disabled)
ICON_OK: str = ""          # No issues

# =============================================================================
# RESOLUTION ACTIONS (for conflict dialog)
# =============================================================================

RESOLUTION_KEEP: str = "keep"
RESOLUTION_UNMAP: str = "unmap"
RESOLUTION_DELETE: str = "delete"
RESOLUTION_REMAP: str = "remap"
RESOLUTION_GARBAGE: str = "garbage"

# =============================================================================
# STYLESHEET
# =============================================================================

EDITOR_STYLESHEET: str = """
QMainWindow {
    background-color: #2b2b2b;
}

QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 11px;
}

QPushButton {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border-color: #90caf9;
}

QPushButton:pressed {
    background-color: #353535;
}

QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}

QPushButton#dangerBtn {
    border-color: #ef5350;
}

QPushButton#dangerBtn:hover {
    background-color: #5a3030;
    border-color: #ff6659;
}

QPushButton#successBtn {
    border-color: #81c784;
}

QPushButton#successBtn:hover {
    background-color: #305030;
    border-color: #a5d6a7;
}

QLineEdit {
    background-color: #1e1e1e;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
}

QLineEdit:focus {
    border-color: #90caf9;
}

QComboBox {
    background-color: #404040;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #90caf9;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    border: 1px solid #555555;
    selection-background-color: #264f78;
}

QTreeWidget {
    background-color: #1e1e1e;
    border: 1px solid #555555;
    border-radius: 4px;
    alternate-background-color: #252525;
    gridline-color: #333333;
}

QTreeWidget::item {
    padding: 2px 4px;
    border: none;
}

QTreeWidget::item:selected {
    background-color: #264f78;
}

QTreeWidget::item:hover {
    background-color: #3a3a3a;
}

QHeaderView::section {
    background-color: #383838;
    color: #e0e0e0;
    padding: 6px 4px;
    border: 1px solid #555555;
    font-weight: bold;
}

QHeaderView::section:hover {
    background-color: #404040;
}

QStatusBar {
    background-color: #252525;
    color: #888888;
    border-top: 1px solid #555555;
}

QFrame#separator {
    background-color: #555555;
    max-height: 1px;
    min-height: 1px;
}

QLabel#sectionHeader {
    color: #90caf9;
    font-weight: bold;
    font-size: 12px;
}

QLabel#statsLabel {
    color: #888888;
    font-size: 10px;
}

QLabel#issueLabel {
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
}

QLabel#issueLabel[issue="duplicate"] {
    background-color: #5a2020;
    color: #ef5350;
}

QLabel#issueLabel[issue="conflict"] {
    background-color: #5a4020;
    color: #ffb74d;
}

QLabel#issueLabel[issue="orphan"] {
    background-color: #402050;
    color: #ce93d8;
}

QDialog {
    background-color: #2b2b2b;
}

QGroupBox {
    border: 1px solid #555555;
    border-radius: 4px;
    margin-top: 12px;
    padding: 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #90caf9;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QListWidget {
    background-color: #1e1e1e;
    border: 1px solid #555555;
    border-radius: 4px;
}

QListWidget::item {
    padding: 4px;
}

QListWidget::item:selected {
    background-color: #264f78;
}

QRadioButton {
    spacing: 6px;
}

QRadioButton::indicator {
    width: 14px;
    height: 14px;
}
"""
