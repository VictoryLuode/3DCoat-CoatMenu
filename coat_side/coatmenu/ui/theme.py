"""CoatMenu - visual constants for the popup.

Kept in one place so the look can be tuned without touching widget logic.
Colours deliberately mirror 3DCoat's own dark chrome (grey-blue, low contrast)
so the popup reads as part of the application rather than as a foreign window.
"""
from __future__ import annotations

# --- window ---
CORNER_RADIUS = 0      # square corners: matches 3DCoat's own menus
ROW_CORNER_RADIUS = 0  # highlight bar corners
BORDER_WIDTH = 1
PADDING = 6
SHADOW_BLUR = 24
FADE_MS = 110

# --- rows ---
ROW_HEIGHT = 24
ROW_PADDING_H = 10
SEPARATOR_HEIGHT = 7
HEADER_HEIGHT = 20
TITLE_HEIGHT = 24
FONT_SIZE = 9          # points, matching LKS's radial menu type size
FONT_FAMILY = "Segoe UI"

# --- colours (r, g, b, a) - tuned to 3DCoat's dark chrome / LKS palette ---
BG = (43, 43, 43, 240)
BORDER = (85, 85, 85, 200)
TEXT = (224, 224, 224)
TEXT_DIM = (136, 136, 136)
HOVER_BG = (58, 106, 160, 255)
HOVER_TEXT = (255, 255, 255)
ACCENT = (144, 202, 249)
SEPARATOR = (255, 255, 255, 24)

# --- behaviour ---
POLL_MS = 10          # key-poll interval while the popup is open
FADE_IN = True
SUBMENU_OVERLAP = 6   # px the child panel overlaps its parent (no dead gap)
SUBMENU_GRACE_MS = 160  # leave grace before a child panel closes
CURSOR_POLL_MS = 10   # how often a panel re-reads the real pointer position

# --- submenu arrow (drawn, not a font glyph) ---
ARROW_WIDTH = 5
ARROW_HEIGHT = 8
