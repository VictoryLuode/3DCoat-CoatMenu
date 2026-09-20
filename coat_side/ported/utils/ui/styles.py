"""LKS UI Styles — re-exported from ported.lks_utils theme system.

Backward-compatible color constants and DARK_STYLESHEET are provided
by mapping ported.lks_utils COLORS keys to the legacy 3DCoat names.

New code should prefer ``from ported.lks_utils.gui_qt.theme.colors import COLORS``
and ``from ported.lks_utils.gui_qt.theme.dark_theme import DARK_QSS``.
"""
from __future__ import annotations

from ported.lks_utils.gui_qt.theme.dark_theme import DARK_QSS, apply_dark_theme
from ported.lks_utils.gui_qt.theme.colors import COLORS as _C

# =============================================================================
# Backward-compatible color constants (mapped from ported.lks_utils COLORS)
# =============================================================================

# Background colors
COLOR_BG_PRIMARY: str = "#2b2b2b"     # 3DCoat uses #2b2b2b (ported.lks_utils uses #222222)
COLOR_BG_SECONDARY: str = _C["input_bg"]  # #2d2d2d
COLOR_BG_BUTTON: str = _C["dark"]         # #303030
COLOR_BG_BUTTON_HOVER: str = "#4a4a4a"    # 3DCoat specific
COLOR_BG_BUTTON_PRESSED: str = "#353535"  # 3DCoat specific
COLOR_BG_BUTTON_DISABLED: str = "#333333" # 3DCoat specific
COLOR_BG_HIGHLIGHT: str = "#264f78"       # 3DCoat specific (selection)
COLOR_BG_TREE_ALT: str = _C["tree_alt_bg"]      # #252525
COLOR_BG_HEADER: str = _C["header_bg"]           # #383838
COLOR_BG_TOOLTIP: str = _C["tooltip_bg"]          # #3c3c3c
COLOR_BG_TAB: str = _C["tab_bg"]                  # #353535
COLOR_BG_TREE_HOVER: str = _C["tree_hover_bg"]    # #3a3a3a

# Text colors
COLOR_TEXT_PRIMARY: str = _C["fg"]          # #ffffff
COLOR_TEXT_MUTED: str = "#888888"           # 3DCoat specific
COLOR_TEXT_DISABLED: str = _C["disabled_fg"]  # #666666

# Accent colors
COLOR_ACCENT: str = "#90caf9"       # 3DCoat specific (icy blue)
COLOR_ACCENT_ALT: str = "#ffb74d"   # 3DCoat specific (orange accent)
COLOR_SUCCESS: str = "#81c784"      # 3DCoat specific
COLOR_WARNING: str = _C["warning"]  # #f39c12
COLOR_ERROR: str = _C["danger"]     # #e74c3c

# Border/separator colors
COLOR_BORDER: str = _C["border"]         # #444444
COLOR_BORDER_LIGHT: str = "#666666"      # 3DCoat specific
COLOR_BORDER_INPUT: str = "#3d3d3d"      # 3DCoat specific
COLOR_BORDER_INPUT_FOCUS: str = "#4a4a4a"  # 3DCoat specific

# Scrollbar colors
COLOR_SCROLLBAR_BG: str = _C["scrollbar_bg"]          # #3a3a3a
COLOR_SCROLLBAR_HANDLE: str = _C["scrollbar_handle"]   # #808080
COLOR_SCROLLBAR_HANDLE_HOVER: str = _C["scrollbar_handle_hover"]  # #A0A0A0

# Side ribbon colors
COLOR_RIBBON_BAR_BG: str = COLOR_BG_PRIMARY            # "#2b2b2b"
COLOR_RIBBON_BAR_BG_HOVER: str = "#3a3a3a"             # 3DCoat specific
COLOR_RIBBON_BAR_BORDER: str = COLOR_BORDER            # "#444444"
COLOR_RIBBON_BAR_TEXT: str = COLOR_ACCENT              # "#90caf9"

# =============================================================================
# DARK THEME STYLESHEET (backward-compatible alias)
# =============================================================================

# ported.lks_utils DARK_QSS applies generous button sizing (min-width: 80px,
# padding: 6px 16px, blue #375a7f background).  3DCoat's compact tool
# panel needs tighter, grayscale buttons.  We append an override block.
#
# ALSO: DARK_QSS contains QTreeView::branch { background-color: #252525 }
# rules that render native branch arrows invisible on Windows by painting
# a dark background over the arrow area.  We strip those rules to allow
# native arrows to follow palette WindowText color.
#
# ALSO: DARK_QSS sets QTreeWidget::item:alternate { background-color: ... }
# while base ::item has no background. Qt then paints alternate rows via the
# stylesheet item path and non-alternate via the style/palette path, which
# shifts icons+text by ~1-2px (zebra sawtooth). Zebra must use the widget
# property alternate-background-color / QPalette.AlternateBase only.
import re

_DARK_QSS_STRIPPED: str = re.sub(
    r'QTreeView::branch[^{]*\{[^}]*\}', '', DARK_QSS, flags=re.DOTALL)
_DARK_QSS_STRIPPED = re.sub(
    r'QTreeWidget::item:alternate,\s*QTreeView::item:alternate\s*\{[^}]*\}',
    '',
    _DARK_QSS_STRIPPED,
    flags=re.DOTALL,
)

# ── 3DCoat compact override sizing constants ──
_FONT_FAMILY: str = "'Consolas', 'Cascadia Code', 'Courier New', monospace"
_BTN_BG: str = "#3a3a3a"
_BTN_BORDER: str = "#555555"
_BTN_BORDER_RADIUS: str = "3px"
_BTN_PADDING: str = "3px 8px"
_BTN_FONT_SIZE: str = "11px"
_BTN_HOVER_BG: str = "#4a4a4a"
_BTN_HOVER_BORDER: str = "#666666"
_BTN_PRESSED_BG: str = "#2a2a2a"
_BTN_DISABLED_BG: str = "#333333"
_BTN_DISABLED_COLOR: str = "#666666"
_TREE_FONT_SIZE: str = "10px"
# Identical box model on every row — never differ by :alternate.
# Keep in sync with ui.radial_menu_theme.TREE_ITEM_*.
_TREE_ITEM_PADDING: str = "0px 2px"
_TREE_ITEM_BORDER: str = "none"
_TREE_ITEM_MARGIN: str = "0px"
_HEADER_PADDING: str = "1px 2px"
_HEADER_FONT_SIZE: str = "9px"

_3DCOAT_BUTTON_OVERRIDE: str = f"""
QWidget {{
    font-family: {_FONT_FAMILY};
}}
QPushButton {{
    background-color: {_BTN_BG};
    border: 1px solid {_BTN_BORDER};
    border-radius: {_BTN_BORDER_RADIUS};
    padding: {_BTN_PADDING};
    min-width: 0px;
    font-size: {_BTN_FONT_SIZE};
}}
QPushButton:hover {{
    background-color: {_BTN_HOVER_BG};
    border-color: {_BTN_HOVER_BORDER};
}}
QPushButton:pressed {{
    background-color: {_BTN_PRESSED_BG};
}}
QPushButton:disabled {{
    background-color: {_BTN_DISABLED_BG};
    color: {_BTN_DISABLED_COLOR};
}}
QTreeWidget {{
    font-size: {_TREE_FONT_SIZE};
}}
QTreeWidget::item, QTreeView::item {{
    padding: {_TREE_ITEM_PADDING};
    border: {_TREE_ITEM_BORDER};
    margin: {_TREE_ITEM_MARGIN};
}}
QTreeWidget::item:alternate, QTreeView::item:alternate {{
    padding: {_TREE_ITEM_PADDING};
    border: {_TREE_ITEM_BORDER};
    margin: {_TREE_ITEM_MARGIN};
}}
QHeaderView::section {{
    padding: {_HEADER_PADDING};
    font-size: {_HEADER_FONT_SIZE};
}}
"""

DARK_STYLESHEET: str = _DARK_QSS_STRIPPED + _3DCOAT_BUTTON_OVERRIDE

# Re-export apply_dark_theme for convenience
__all__ = [
    "DARK_STYLESHEET",
    "DARK_QSS",
    "apply_dark_theme",
    "COLOR_BG_PRIMARY",
    "COLOR_BG_SECONDARY",
    "COLOR_BG_BUTTON",
    "COLOR_BG_BUTTON_HOVER",
    "COLOR_BG_BUTTON_PRESSED",
    "COLOR_BG_BUTTON_DISABLED",
    "COLOR_BG_HIGHLIGHT",
    "COLOR_BG_TREE_ALT",
    "COLOR_BG_HEADER",
    "COLOR_BG_TOOLTIP",
    "COLOR_BG_TAB",
    "COLOR_BG_TREE_HOVER",
    "COLOR_TEXT_PRIMARY",
    "COLOR_TEXT_MUTED",
    "COLOR_TEXT_DISABLED",
    "COLOR_ACCENT",
    "COLOR_ACCENT_ALT",
    "COLOR_SUCCESS",
    "COLOR_WARNING",
    "COLOR_ERROR",
    "COLOR_BORDER",
    "COLOR_BORDER_LIGHT",
    "COLOR_BORDER_INPUT",
    "COLOR_BORDER_INPUT_FOCUS",
    "COLOR_SCROLLBAR_BG",
    "COLOR_SCROLLBAR_HANDLE",
    "COLOR_SCROLLBAR_HANDLE_HOVER",
    "COLOR_RIBBON_BAR_BG",
    "COLOR_RIBBON_BAR_BG_HOVER",
    "COLOR_RIBBON_BAR_BORDER",
    "COLOR_RIBBON_BAR_TEXT",
]
