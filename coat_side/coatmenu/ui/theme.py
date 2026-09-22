"""CoatMenu - visual constants for the popup.

Kept in one place so the look can be tuned without touching widget logic.
Colours deliberately mirror 3DCoat's own dark chrome (grey-blue, low contrast)
so the popup reads as part of the application rather than as a foreign window.
"""
from __future__ import annotations

# --- window ---
CORNER_RADIUS = 3      # a very small rounding on the panel itself
ROW_CORNER_RADIUS = 2  # the highlight bar is rounded to match
BORDER_WIDTH = 1
PADDING = 6
FADE_MS = 110

# --- rows ---
ROW_HEIGHT = 24
ROW_PADDING_H = 10
SEPARATOR_HEIGHT = 7
HEADER_HEIGHT = 20
TITLE_HEIGHT = 24

# A list taller than this scrolls instead of running off the screen. 3DCoat is
# used full-screen, and a menu whose last rows are unreachable looks broken.
MAX_MENU_HEIGHT = 560
SCROLLBAR_W = 3
FONT_SIZE = 9          # points, matching 3DCoat's own menu type size
FONT_FAMILY = "Segoe UI"

# --- colours (r, g, b, a) - tuned to 3DCoat's dark chrome ---
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

# --- radial pie mode: Blender's pie layout ---
# Blender does not draw wedges: it lays *buttons* out around the cursor with a
# small ring in the middle (see its Shading pie). Measured from Blender's own
# defaults/prefs: pie_menu_radius = 100 (button centre distance), and a ring of
# roughly 38px diameter at the centre on a 1.5x UI scale.
PIE_SLOT_DISTANCE = 100  # distance from the centre to each button's centre
PIE_SLOT_HEIGHT = 24     # button height, px
PIE_CENTRE_RING = 38     # centre ring diameter, px
PIE_BUTTON_RADIUS = 4    # button corner radius (Blender's buttons are rounded)
PIE_BUTTON_MIN_W = 64    # narrowest button
PIE_BUTTON_MAX_W = 168   # widest button (long labels elide beyond this)
PIE_DIGIT_HINT_W = 16    # room reserved for the "1..9" shortcut hint
PIE_INLINE_MAX = 3       # a slot with this many children or fewer opens in place
PIE_BUTTON_GAP = 2       # gap between stacked buttons of one slot
PIE_DWELL_MS = 160       # hover time on a branch before its submenu opens
PIE_LABEL_SIZE = 9       # point size for button labels
SEGMENT_BG = (52, 54, 58, 235)  # button fill (HOVER_BG marks the pointed-at one)
