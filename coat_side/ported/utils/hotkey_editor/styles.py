"""
Hotkey Editor - Constants and Styles

All UI constants, colors, and stylesheet for the hotkey editor.
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

DEFAULT_GARBAGE_KEY: str = "END"
DEFAULT_GARBAGE_CTRL: bool = True
DEFAULT_GARBAGE_ALT: bool = False
DEFAULT_GARBAGE_SHIFT: bool = False

# =============================================================================
# STATUS COLORS
# =============================================================================

COLOR_DUPLICATE: str = "#ef5350"
COLOR_CONFLICT: str = "#ffb74d"
COLOR_ORPHAN: str = "#ce93d8"
COLOR_NORMAL: str = "#e0e0e0"
COLOR_UNASSIGNED: str = "#666666"
COLOR_GARBAGE: str = "#78909c"

# =============================================================================
# STATUS ICONS
# =============================================================================

ICON_DUPLICATE: str = "⊗"
ICON_CONFLICT: str = "⚡"
ICON_ORPHAN: str = "?"
ICON_GARBAGE: str = "🗑️"
ICON_OK: str = ""

# =============================================================================
# RESOLUTION ACTIONS
# =============================================================================

RESOLUTION_KEEP: str = "keep"
RESOLUTION_UNMAP: str = "unmap"
RESOLUTION_DELETE: str = "delete"
RESOLUTION_REMAP: str = "remap"
RESOLUTION_GARBAGE: str = "garbage"


# =============================================================================
# STYLESHEET BUILDER
# =============================================================================

def _build_stylesheet() -> str:
    """Build the editor stylesheet dynamically."""
    bg_main = "#2b2b2b"
    bg_dark = "#1e1e1e"
    bg_button = "#404040"
    bg_hover = "#4a4a4a"
    bg_pressed = "#353535"
    bg_disabled = "#333333"
    bg_header = "#383838"
    bg_selection = "#264f78"
    bg_item_hover = "#3a3a3a"
    bg_status = "#252525"

    border_normal = "#555555"
    border_accent = "#90caf9"
    border_danger = "#ef5350"
    border_success = "#81c784"

    text_normal = "#e0e0e0"
    text_muted = "#888888"
    text_disabled = "#666666"
    text_accent = "#90caf9"

    return f"""
QMainWindow {{
    background-color: {bg_main};
}}

QWidget {{
    background-color: {bg_main};
    color: {text_normal};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 11px;
}}

QPushButton {{
    background-color: {bg_button};
    border: 1px solid {border_normal};
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {bg_hover};
    border-color: {border_accent};
}}

QPushButton:pressed {{
    background-color: {bg_pressed};
}}

QPushButton:disabled {{
    background-color: {bg_disabled};
    color: {text_disabled};
}}

QPushButton#dangerBtn {{
    border-color: {border_danger};
}}

QPushButton#dangerBtn:hover {{
    background-color: #5a3030;
    border-color: #ff6659;
}}

QPushButton#successBtn {{
    border-color: {border_success};
}}

QPushButton#successBtn:hover {{
    background-color: #305030;
    border-color: #a5d6a7;
}}

QLineEdit {{
    background-color: {bg_dark};
    border: 1px solid {border_normal};
    border-radius: 4px;
    padding: 4px 8px;
}}

QLineEdit:focus {{
    border-color: {border_accent};
}}

QComboBox {{
    background-color: {bg_button};
    border: 1px solid {border_normal};
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {border_accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_main};
    border: 1px solid {border_normal};
    selection-background-color: {bg_selection};
}}

QTreeWidget {{
    background-color: {bg_dark};
    border: 1px solid {border_normal};
    border-radius: 4px;
    alternate-background-color: #252525;
    gridline-color: #333333;
}}

QTreeWidget::item {{
    padding: 2px 4px;
    border: none;
}}

QTreeWidget::item:selected {{
    background-color: {bg_selection};
}}

QTreeWidget::item:hover {{
    background-color: {bg_item_hover};
}}

QHeaderView::section {{
    background-color: {bg_header};
    color: {text_normal};
    padding: 6px 4px;
    border: 1px solid {border_normal};
    font-weight: bold;
}}

QHeaderView::section:hover {{
    background-color: {bg_button};
}}

QStatusBar {{
    background-color: {bg_status};
    color: {text_muted};
    border-top: 1px solid {border_normal};
}}

QFrame#separator {{
    background-color: {border_normal};
    max-height: 1px;
    min-height: 1px;
}}

QLabel#sectionHeader {{
    color: {text_accent};
    font-weight: bold;
    font-size: 12px;
}}

QLabel#statsLabel {{
    color: {text_muted};
    font-size: 10px;
}}

QLabel#issueLabel {{
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
}}

QLabel#issueLabel[issue="duplicate"] {{
    background-color: #5a2020;
    color: {COLOR_DUPLICATE};
}}

QLabel#issueLabel[issue="conflict"] {{
    background-color: #5a4020;
    color: {COLOR_CONFLICT};
}}

QLabel#issueLabel[issue="orphan"] {{
    background-color: #402050;
    color: {COLOR_ORPHAN};
}}

QDialog {{
    background-color: {bg_main};
}}

QGroupBox {{
    border: 1px solid {border_normal};
    border-radius: 4px;
    margin-top: 12px;
    padding: 8px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {text_accent};
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QListWidget {{
    background-color: {bg_dark};
    border: 1px solid {border_normal};
    border-radius: 4px;
}}

QListWidget::item {{
    padding: 4px;
}}

QListWidget::item:selected {{
    background-color: {bg_selection};
}}

QRadioButton {{
    spacing: 6px;
}}

QRadioButton::indicator {{
    width: 14px;
    height: 14px;
}}
"""


EDITOR_STYLESHEET: str = _build_stylesheet()
