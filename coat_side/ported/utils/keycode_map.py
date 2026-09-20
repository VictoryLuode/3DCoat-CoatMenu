"""
3DCoat Hotkey Keycode Mapping Constants.

Maps Qt key names / physical keys to 3DCoat's internal XML keycode representation.
Used for bidirectional conversion in the hotkey editor.

Reference: _docs/3dcoat_hotkey_keycodes.md

Legend:
  ✅ = Observed in actual 3DCoat XML output
  ⚠️ = Inferred from pattern (not directly observed)
  ❌ = Known unmappable in 3DCoat
"""

from typing import Final

# =============================================================================
# LETTERS (A-Z) - All uppercase
# =============================================================================
# Pattern: Single uppercase character
# All letters follow the same pattern, sampling several confirms this.

KEY_A: Final[str] = "A"  # ✅ Observed (NAVIFRAME)
KEY_B: Final[str] = "B"  # ✅ Observed (Picker)
KEY_C: Final[str] = "C"  # ✅ Observed (COPY, ID_COLOR_HDR)
KEY_D: Final[str] = "D"  # ✅ Observed (MENU_UNFREEZE_ALL, ID_BUMP_HDR)
KEY_E: Final[str] = "E"  # ✅ Observed (ID_PENOPS, TRANSFORM_ROTATE_FREE)
# ✅ Observed (MENU_TOGGLE_FREEZE_VIEW, rotate_around_custom_point)
KEY_F: Final[str] = "F"
# ✅ Observed (TRANSFORM_TRANSLATE_FREE, Isolate_ghosting)
KEY_G: Final[str] = "G"
KEY_H: Final[str] = "H"  # ✅ Observed (Pick_layer_add, Pick_layer_sub)
# ✅ Observed (MENU_INVERT_FREEZE, Invert_vox_visibility)
KEY_I: Final[str] = "I"
KEY_J: Final[str] = "J"  # ⚠️ Inferred from pattern
KEY_K: Final[str] = "K"  # ✅ Observed (UploadToSketchFab)
KEY_L: Final[str] = "L"  # ⚠️ Inferred from pattern
KEY_M: Final[str] = "M"  # ✅ Observed (IMPORT_PLANE, TRANSFORM_TRANSLATE_SNAP)
KEY_N: Final[str] = "N"  # ✅ Observed (CLEARSCENE, StartObjTransform3D)
KEY_O: Final[str] = "O"  # ✅ Observed (DEC_OPACITY, OPEN_FILE)
KEY_P: Final[str] = "P"  # ✅ Observed (INC_OPACITY)
KEY_Q: Final[str] = "Q"  # ✅ Observed (CurvParamsPopup)
KEY_R: Final[str] = "R"  # ✅ Observed (ID_SPECULAR_HDR, TRANSFORM_SCALE_FREE)
KEY_S: Final[str] = "S"  # ✅ Observed (SYMMETRY, SAVE_FILEFAST, SMOOTH_STROKE)
KEY_T: Final[str] = "T"  # ✅ Observed (Pen, UPLOAD_TURNABLE)
KEY_U: Final[str] = "U"  # ⚠️ Inferred from pattern
# ✅ Observed (PASTE, Pick_color, Toggle_vox_visibility)
KEY_V: Final[str] = "V"
KEY_W: Final[str] = "W"  # ✅ Observed (VIEW_WIREFRAME, VIEW_SEAMS)
# ✅ Observed (TRANSFORM_TRANSLATE_X, ToUniformSpaceAll)
KEY_X: Final[str] = "X"
KEY_Y: Final[str] = "Y"  # ✅ Observed (REDO, TRANSFORM_TRANSLATE_Y, CameraRedo)
KEY_Z: Final[str] = "Z"  # ✅ Observed (UNDO, TRANSFORM_TRANSLATE_Z, CameraUndo)


# =============================================================================
# NUMBERS (Top Row 0-9)
# =============================================================================
# Pattern: Single digit character

KEY_0: Final[str] = "0"  # ✅ Observed (DEC_ANGLE)
KEY_1: Final[str] = "1"  # ✅ Observed (VIEW_RELIEF_ONLY)
KEY_2: Final[str] = "2"  # ✅ Observed (VIEW_NON_SHADED, preset Shift+2)
KEY_3: Final[str] = "3"  # ✅ Observed (VIEW_GLOSS_ONLY)
KEY_4: Final[str] = "4"  # ⚠️ Inferred from pattern
KEY_5: Final[str] = "5"  # ✅ Observed (VIEW_SHADED)
KEY_6: Final[str] = "6"  # ✅ Observed (VIEW_LOWPOLY, VoxTreeBranch Shift+6)
# ✅ Observed (VIEW_SPECULAR_COLOR_ONLY, preset Shift+7)
KEY_7: Final[str] = "7"
KEY_8: Final[str] = "8"  # ✅ Observed (VIEW_METALNESS_ONLY, preset Shift+8)
KEY_9: Final[str] = "9"  # ✅ Observed (INC_ANGLE)


# =============================================================================
# NUMPAD KEYS
# =============================================================================
# Pattern: NUM prefix + digit (no underscore for digits)
# WARNING: Inconsistent naming! See comments.

KEY_NUM0: Final[str] = "NUM0"  # ⚠️ Inferred from pattern
KEY_NUM1: Final[str] = "NUM1"  # ✅ Observed (VIEW_BOTTOM)
KEY_NUM2: Final[str] = "NUM2"  # ✅ Observed (VIEW_FRONT)
KEY_NUM3: Final[str] = "NUM3"  # ⚠️ Inferred from pattern
KEY_NUM4: Final[str] = "NUM4"  # ✅ Observed (VIEW_LEFT)
KEY_NUM5: Final[str] = "NUM5"  # ✅ Observed (VIEW_ORTHO)
KEY_NUM6: Final[str] = "NUM6"  # ✅ Observed (VIEW_RIGHT)
KEY_NUM7: Final[str] = "NUM7"  # ✅ Observed (VIEW_TOP)
KEY_NUM8: Final[str] = "NUM8"  # ✅ Observed (VIEW_BACK)
KEY_NUM9: Final[str] = "NUM9"  # ⚠️ Inferred from pattern

# Numpad operators - INCONSISTENT NAMING!
# ✅ Observed (MENU_FREEZE_BORDER) - NO underscore
KEY_NUM_DIVIDE: Final[str] = "NUM/"
# ✅ Observed (MENU_BLUR_FREEZE) - NO underscore
KEY_NUM_MULTIPLY: Final[str] = "NUM*"
# ✅ Observed (MENU_EXPAND_FREEZE, PolynomeBackground::plBack) - HAS underscore!
KEY_NUM_MINUS: Final[str] = "NUM_MINUS"
# ✅ Observed (preset LKS AddVox, PolynomeBackground::plForward) - HAS underscore!
KEY_NUM_PLUS: Final[str] = "NUM_PLUS"
# ✅ Observed (preset LKS AddVox BoxLine) - Uses SCANCODE!
KEY_NUM_DECIMAL: Final[str] = "key_6E"
# ❌ UNMAPPABLE - 3DCoat doesn't distinguish from main Enter
KEY_NUM_ENTER: Final[str] = None


# =============================================================================
# FUNCTION KEYS (F1-F12)
# =============================================================================
# Pattern: F + number

KEY_F1: Final[str] = "F1"    # ✅ Observed (preset LKS VoxBlockin)
KEY_F2: Final[str] = "F2"    # ⚠️ Inferred from pattern
KEY_F3: Final[str] = "F3"    # ⚠️ Inferred from pattern
KEY_F4: Final[str] = "F4"    # ⚠️ Inferred from pattern
KEY_F5: Final[str] = "F5"    # ⚠️ Inferred from pattern
KEY_F6: Final[str] = "F6"    # ⚠️ Inferred from pattern
KEY_F7: Final[str] = "F7"    # ⚠️ Inferred from pattern
KEY_F8: Final[str] = "F8"    # ⚠️ Inferred from pattern
KEY_F9: Final[str] = "F9"    # ✅ Observed (ModifyHint)
KEY_F10: Final[str] = "F10"  # ⚠️ Inferred from pattern
KEY_F11: Final[str] = "F11"  # ✅ Observed (HighlightSelected)
KEY_F12: Final[str] = "F12"  # ⚠️ Inferred from pattern


# =============================================================================
# SPECIAL / NAMED KEYS
# =============================================================================
# WARNING: Inconsistent casing and abbreviation!

KEY_ENTER: Final[str] = "ENTER"    # ✅ Observed (Execute, ToggleFullscreen)
KEY_ESCAPE: Final[str] = "ESC"     # ✅ Observed (Escape)
KEY_SPACE: Final[str] = "SPACE"    # ✅ Observed (SHOW_TOOLS_PALETTE)
KEY_TAB: Final[str] = "Tab"        # ✅ Observed (ToggleUI) - Mixed case!
# ❌ UNMAPPABLE - reserved for Clear in 3DCoat
KEY_BACKSPACE: Final[str] = None
# ✅ Observed (preset LKS ClayBuildup Round) - Full word
KEY_DELETE: Final[str] = "DELETE"
# ✅ Observed (preset LKS Vox Draw Square) - Abbreviated!
KEY_INSERT: Final[str] = "INS"
KEY_HOME: Final[str] = "HOME"      # ✅ Observed (preset LKS Clone Lasso)
KEY_END: Final[str] = None         # ❌ UNMAPPABLE
KEY_PAGE_UP: Final[str] = "PGUP"   # ✅ Observed (preset LKS Move Smudge)
KEY_PAGE_DOWN: Final[str] = "PGDN"  # ✅ Observed (preset LKS Mask Paint)


# =============================================================================
# ARROW KEYS
# =============================================================================
# Pattern: Capitalized names

KEY_UP: Final[str] = "Up"        # ✅ Observed (ADD_CAM_PRESET)
KEY_DOWN: Final[str] = "Down"    # ✅ Observed (DEL_CAM_PRESET)
KEY_LEFT: Final[str] = "Left"    # ✅ Observed (PREV_CAM_PRESET)
KEY_RIGHT: Final[str] = "Right"  # ✅ Observed (NEXT_CAM_PRESET)


# =============================================================================
# SYMBOL KEYS - Literal Storage
# =============================================================================
# These characters are stored as-is (no encoding needed)

KEY_BACKTICK: Final[str] = "`"          # ⚠️ Inferred (grave accent, below Esc)
# ✅ Observed (QuickPanel, preset LKS ClayBuildup Square)
KEY_TILDE: Final[str] = "~"
# ✅ Observed (DEC_DEGREE, DEC_SM_DEGREE)
KEY_MINUS: Final[str] = "-"
KEY_EQUALS: Final[str] = "="            # ⚠️ Inferred from pattern
# ✅ Observed (INC_DEGREE, INC_SM_DEGREE)
KEY_PLUS: Final[str] = "+"
# ✅ Observed (DEC_RADIUS, preset LKS Pose Object FFD)
KEY_BRACKET_LEFT: Final[str] = "["
KEY_BRACKET_RIGHT: Final[str] = "]"     # ✅ Observed (INC_RADIUS)
# ⚠️ Inferred (scancode 0xDC = VK_OEM_5)
KEY_BACKSLASH: Final[str] = "key_DC"
KEY_SEMICOLON: Final[str] = ";"         # ✅ Observed (DEC_SPEC_OPACITY)
# ✅ Observed (INC_SPEC_OPACITY, SHOW_GRID, preset LKS Move Soft)
KEY_APOSTROPHE: Final[str] = "'"
KEY_SLASH: Final[str] = "/"             # ⚠️ Inferred from pattern
# ✅ Observed (preset LKS CutOff Lasso, preset LKS VoxClay)
KEY_QUESTION: Final[str] = "?"


# =============================================================================
# SYMBOL KEYS - XML Entity Encoding Required (CRITICAL!)
# =============================================================================
# These use SHIFTED character storage pattern!
# See _docs/3dcoat_hotkey_keycodes.md for full explanation.

# Period (.) and Greater-than (>) share the same physical key
# 3DCoat stores BOTH as ">" - the Shift field distinguishes them
# ✅ Observed (select Cube_01 with Shift=false = period)
KEY_PERIOD: Final[str] = "&gt"
# ✅ Observed (select Cube with Shift=true)
KEY_GREATER_THAN: Final[str] = "&gt"

# Comma (,) and Less-than (<) share the same physical key
# 3DCoat stores BOTH as "<" - the Shift field distinguishes them
# ✅ Observed (select Cube_Chamfer with Shift=false = comma)
KEY_COMMA: Final[str] = "&lt"
# ✅ Observed (select Cube_Fillet with Shift=true)
KEY_LESS_THAN: Final[str] = "&lt"


# =============================================================================
# SCANCODE FORMAT
# =============================================================================
# Used for keys that can't be represented as simple characters

KEY_UNASSIGNED: Final[str] = "key_00"   # ✅ Observed (many unbound keys)
# Note: key_T was observed but origin unknown - possibly a bug or special case
# ✅ Observed (preset LKS Vox SoftBuildup) - UNKNOWN ORIGIN
KEY_SCANCODE_T: Final[str] = "key_T"


# =============================================================================
# LOOKUP DICTIONARIES
# =============================================================================

# Qt Key Name -> 3DCoat XML Code
# Use this when WRITING to XML from Qt key events
QT_TO_3DCOAT: dict[str, str | None] = {
    # Letters
    "A": KEY_A, "B": KEY_B, "C": KEY_C, "D": KEY_D, "E": KEY_E,
    "F": KEY_F, "G": KEY_G, "H": KEY_H, "I": KEY_I, "J": KEY_J,
    "K": KEY_K, "L": KEY_L, "M": KEY_M, "N": KEY_N, "O": KEY_O,
    "P": KEY_P, "Q": KEY_Q, "R": KEY_R, "S": KEY_S, "T": KEY_T,
    "U": KEY_U, "V": KEY_V, "W": KEY_W, "X": KEY_X, "Y": KEY_Y, "Z": KEY_Z,

    # Numbers
    "0": KEY_0, "1": KEY_1, "2": KEY_2, "3": KEY_3, "4": KEY_4,
    "5": KEY_5, "6": KEY_6, "7": KEY_7, "8": KEY_8, "9": KEY_9,

    # Numpad - Qt uses Key_* naming
    "Key_0": KEY_NUM0, "Key_1": KEY_NUM1, "Key_2": KEY_NUM2,
    "Key_3": KEY_NUM3, "Key_4": KEY_NUM4, "Key_5": KEY_NUM5,
    "Key_6": KEY_NUM6, "Key_7": KEY_NUM7, "Key_8": KEY_NUM8, "Key_9": KEY_NUM9,
    "Key_Slash": KEY_NUM_DIVIDE,
    "Key_Asterisk": KEY_NUM_MULTIPLY,
    "Key_Minus": KEY_NUM_MINUS,
    "Key_Plus": KEY_NUM_PLUS,
    "Key_Period": KEY_NUM_DECIMAL,
    "Key_Enter": KEY_NUM_ENTER,  # None - unmappable

    # Function keys
    "F1": KEY_F1, "F2": KEY_F2, "F3": KEY_F3, "F4": KEY_F4,
    "F5": KEY_F5, "F6": KEY_F6, "F7": KEY_F7, "F8": KEY_F8,
    "F9": KEY_F9, "F10": KEY_F10, "F11": KEY_F11, "F12": KEY_F12,

    # Special keys
    "Return": KEY_ENTER,
    "Enter": KEY_ENTER,
    "Escape": KEY_ESCAPE,
    "Space": KEY_SPACE,
    "Tab": KEY_TAB,
    "Backspace": KEY_BACKSPACE,  # None - unmappable
    "Delete": KEY_DELETE,
    "Insert": KEY_INSERT,
    "Home": KEY_HOME,
    "End": KEY_END,  # None - unmappable
    "PageUp": KEY_PAGE_UP,
    "PageDown": KEY_PAGE_DOWN,

    # Arrow keys
    "Up": KEY_UP,
    "Down": KEY_DOWN,
    "Left": KEY_LEFT,
    "Right": KEY_RIGHT,

    # Symbols
    "QuoteLeft": KEY_BACKTICK,  # ` (grave/backtick)
    "AsciiTilde": KEY_TILDE,    # ~
    "Minus": KEY_MINUS,
    "Equal": KEY_EQUALS,
    "Plus": KEY_PLUS,
    "BracketLeft": KEY_BRACKET_LEFT,
    "BracketRight": KEY_BRACKET_RIGHT,
    "Backslash": KEY_BACKSLASH,
    "Semicolon": KEY_SEMICOLON,
    "Apostrophe": KEY_APOSTROPHE,
    "Comma": KEY_COMMA,         # Stored as &lt !
    "Period": KEY_PERIOD,       # Stored as &gt !
    "Slash": KEY_SLASH,
    "Question": KEY_QUESTION,
    "Less": KEY_LESS_THAN,      # Stored as &lt
    "Greater": KEY_GREATER_THAN,  # Stored as &gt
}


# 3DCoat XML Code -> Display String (for UI)
# Use this when READING from XML to show user-friendly names
# Note: For < and >, must also check Shift field to determine actual key
COAT_TO_DISPLAY: dict[str, str] = {
    # Letters - display as-is
    **{c: c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},

    # Numbers - display as-is
    **{c: c for c in "0123456789"},

    # Numpad
    "NUM0": "Num 0", "NUM1": "Num 1", "NUM2": "Num 2",
    "NUM3": "Num 3", "NUM4": "Num 4", "NUM5": "Num 5",
    "NUM6": "Num 6", "NUM7": "Num 7", "NUM8": "Num 8", "NUM9": "Num 9",
    "NUM/": "Num /",
    "NUM*": "Num *",
    "NUM_MINUS": "Num -",
    "NUM_PLUS": "Num +",
    "key_6E": "Num .",

    # Function keys
    **{f"F{i}": f"F{i}" for i in range(1, 13)},

    # Special keys
    "ENTER": "Enter",
    "ESC": "Esc",
    "SPACE": "Space",
    "Tab": "Tab",
    "DELETE": "Delete",
    "INS": "Insert",
    "HOME": "Home",
    "PGUP": "Page Up",
    "PGDN": "Page Down",

    # Arrow keys
    "Up": "↑",
    "Down": "↓",
    "Left": "←",
    "Right": "→",

    # Symbols
    "`": "`",
    "~": "~",
    "-": "-",
    "=": "=",
    "+": "+",
    "[": "[",
    "]": "]",
    "key_DC": "\\",
    ";": ";",
    "'": "'",
    "/": "/",
    "?": "?",

    # Entity-encoded (need Shift field context - see get_display_key())
    ">": ">",  # or "." if Shift=false
    "<": "<",  # or "," if Shift=false

    # Scancodes
    "key_00": "(None)",
    "key_T": "??? (key_T)",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_display_key(code: str, shift: bool = False) -> str:
    """
    Convert 3DCoat XML code to display string.

    Args:
        code: The Code field value from XML (may be entity-decoded)
        shift: The Shift field value from XML

    Returns:
        Human-readable key name for UI display
    """
    # Handle the shifted-character storage pattern for . and ,
    if code == ">":
        return ">" if shift else "."
    if code == "<":
        return "<" if shift else ","

    return COAT_TO_DISPLAY.get(code, code)


def get_coat_code(display_key: str) -> tuple[str, bool]:
    """
    Convert display/input key to 3DCoat XML code and shift state.

    Args:
        display_key: The key as user sees/types it

    Returns:
        Tuple of (xml_code, shift_required)
    """
    # Handle the shifted-character storage pattern
    if display_key == ".":
        return ("&gt", False)
    if display_key == ">":
        return ("&gt", True)
    if display_key == ",":
        return ("&lt", False)
    if display_key == "<":
        return ("&lt", True)

    # Most keys don't require special handling
    code = QT_TO_3DCOAT.get(display_key.upper(), display_key)
    if code is None:
        return ("key_00", False)  # Unmappable
    return (code, False)


def normalize_manual_input(text: str) -> str:
    """
    Convert manual text input to valid 3DCoat XML code.

    Handles common variations users might type:
    - "space" → "SPACE"
    - "enter" → "ENTER"
    - "escape", "esc" → "ESC"
    - etc.

    Returns the input unchanged if no mapping found.
    """
    normalized = text.strip().upper()

    # Common aliases → 3DCoat XML code
    aliases: dict[str, str] = {
        # Special keys
        "SPACE": KEY_SPACE,
        "ENTER": KEY_ENTER,
        "RETURN": KEY_ENTER,
        "ESCAPE": KEY_ESCAPE,
        "ESC": KEY_ESCAPE,
        "TAB": KEY_TAB,
        "DELETE": KEY_DELETE,
        "DEL": KEY_DELETE,
        "INSERT": KEY_INSERT,
        "INS": KEY_INSERT,
        "HOME": KEY_HOME,
        "PAGEUP": KEY_PAGE_UP,
        "PAGE UP": KEY_PAGE_UP,
        "PGUP": KEY_PAGE_UP,
        "PAGEDOWN": KEY_PAGE_DOWN,
        "PAGE DOWN": KEY_PAGE_DOWN,
        "PGDN": KEY_PAGE_DOWN,
        # Arrows
        "UP": KEY_UP,
        "DOWN": KEY_DOWN,
        "LEFT": KEY_LEFT,
        "RIGHT": KEY_RIGHT,
        # Numpad
        "NUM0": KEY_NUM0, "NUM1": KEY_NUM1, "NUM2": KEY_NUM2,
        "NUM3": KEY_NUM3, "NUM4": KEY_NUM4, "NUM5": KEY_NUM5,
        "NUM6": KEY_NUM6, "NUM7": KEY_NUM7, "NUM8": KEY_NUM8, "NUM9": KEY_NUM9,
        "NUM/": KEY_NUM_DIVIDE,
        "NUM*": KEY_NUM_MULTIPLY,
        "NUM-": KEY_NUM_MINUS,
        "NUM_MINUS": KEY_NUM_MINUS,
        "NUMMINUS": KEY_NUM_MINUS,
        "NUM+": KEY_NUM_PLUS,
        "NUM_PLUS": KEY_NUM_PLUS,
        "NUMPLUS": KEY_NUM_PLUS,
        "NUM.": KEY_NUM_DECIMAL,
        # Symbols
        "GRAVE": KEY_BACKTICK,
        "BACKTICK": KEY_BACKTICK,
        "TILDE": KEY_TILDE,
        "MINUS": KEY_MINUS,
        "EQUAL": KEY_EQUALS,
        "EQUALS": KEY_EQUALS,
        "PLUS": KEY_PLUS,
        "LBRACKET": KEY_BRACKET_LEFT,
        "RBRACKET": KEY_BRACKET_RIGHT,
        "BACKSLASH": KEY_BACKSLASH,
        "SEMICOLON": KEY_SEMICOLON,
        "APOSTROPHE": KEY_APOSTROPHE,
        "QUOTE": KEY_APOSTROPHE,
        "SLASH": KEY_SLASH,
        "QUESTION": KEY_QUESTION,
        "COMMA": KEY_COMMA,
        "PERIOD": KEY_PERIOD,
    }

    if normalized in aliases:
        return aliases[normalized]

    # Single letters and numbers pass through
    if len(normalized) == 1 and normalized.isalnum():
        return normalized

    # Function keys
    if normalized.startswith("F") and normalized[1:].isdigit():
        return normalized

    # Already a valid code, pass through
    return text.strip()


# =============================================================================
# UNMAPPABLE KEYS (for reference)
# =============================================================================
UNMAPPABLE_KEYS: set[str] = {
    "Backspace",   # Reserved for Clear in 3DCoat
    "End",         # Not recognized
    "NumpadEnter",  # Not distinguished from main Enter
}


# =============================================================================
# CONVERSION TO QT KEYCODES
# =============================================================================

def coat_to_qt_key(coat_code: str) -> int | None:
    """
    Convert 3DCoat keycode to Qt.Key constant.

    Args:
        coat_code: 3DCoat keycode string (e.g., "A", "F1", "Space")

    Returns:
        Qt key constant (int) or None if not mappable
    """
    try:
        from PySide6.QtCore import Qt
    except ImportError:
        return None

    # Map common 3DCoat codes to Qt keys
    mapping = {
        # Letters
        "A": Qt.Key_A, "B": Qt.Key_B, "C": Qt.Key_C, "D": Qt.Key_D,
        "E": Qt.Key_E, "F": Qt.Key_F, "G": Qt.Key_G, "H": Qt.Key_H,
        "I": Qt.Key_I, "J": Qt.Key_J, "K": Qt.Key_K, "L": Qt.Key_L,
        "M": Qt.Key_M, "N": Qt.Key_N, "O": Qt.Key_O, "P": Qt.Key_P,
        "Q": Qt.Key_Q, "R": Qt.Key_R, "S": Qt.Key_S, "T": Qt.Key_T,
        "U": Qt.Key_U, "V": Qt.Key_V, "W": Qt.Key_W, "X": Qt.Key_X,
        "Y": Qt.Key_Y, "Z": Qt.Key_Z,

        # Numbers
        "0": Qt.Key_0, "1": Qt.Key_1, "2": Qt.Key_2, "3": Qt.Key_3,
        "4": Qt.Key_4, "5": Qt.Key_5, "6": Qt.Key_6, "7": Qt.Key_7,
        "8": Qt.Key_8, "9": Qt.Key_9,

        # Function keys
        "F1": Qt.Key_F1, "F2": Qt.Key_F2, "F3": Qt.Key_F3, "F4": Qt.Key_F4,
        "F5": Qt.Key_F5, "F6": Qt.Key_F6, "F7": Qt.Key_F7, "F8": Qt.Key_F8,
        "F9": Qt.Key_F9, "F10": Qt.Key_F10, "F11": Qt.Key_F11, "F12": Qt.Key_F12,

        # Special keys
        "Space": Qt.Key_Space,
        "Tab": Qt.Key_Tab,
        "Return": Qt.Key_Return,
        "Escape": Qt.Key_Escape,
        "Delete": Qt.Key_Delete,
        "Home": Qt.Key_Home,
        "PageUp": Qt.Key_PageUp,
        "PageDown": Qt.Key_PageDown,
        "Insert": Qt.Key_Insert,
        "Up": Qt.Key_Up,
        "Down": Qt.Key_Down,
        "Left": Qt.Key_Left,
        "Right": Qt.Key_Right,

        # Symbol keys
        "`": Qt.Key_QuoteLeft,
        "~": Qt.Key_AsciiTilde,
        "-": Qt.Key_Minus,
        "=": Qt.Key_Equal,
        "+": Qt.Key_Plus,
        "[": Qt.Key_BracketLeft,
        "]": Qt.Key_BracketRight,
        "key_DC": Qt.Key_Backslash,
        ";": Qt.Key_Semicolon,
        "'": Qt.Key_Apostrophe,
        "/": Qt.Key_Slash,
        "?": Qt.Key_Question,

        # Entities (3DCoat stores these specially)
        "&gt": Qt.Key_Period,  # Period OR Greater Than (check Shift flag)
        "&lt": Qt.Key_Comma,   # Comma OR Less Than (check Shift flag)

        # Numpad
        "key_60": Qt.Key_0,  # Numpad 0
        "key_61": Qt.Key_1,  # Numpad 1
        "key_62": Qt.Key_2,  # Numpad 2
        "key_63": Qt.Key_3,  # Numpad 3
        "key_64": Qt.Key_4,  # Numpad 4
        "key_65": Qt.Key_5,  # Numpad 5
        "key_66": Qt.Key_6,  # Numpad 6
        "key_67": Qt.Key_7,  # Numpad 7
        "key_68": Qt.Key_8,  # Numpad 8
        "key_69": Qt.Key_9,  # Numpad 9
        "key_6E": Qt.Key_Period,  # Numpad period
        "key_6A": Qt.Key_Asterisk,  # Numpad multiply
        "key_6B": Qt.Key_Plus,  # Numpad add
        "key_6D": Qt.Key_Minus,  # Numpad subtract
        "key_6F": Qt.Key_Slash,  # Numpad divide
    }

    return mapping.get(coat_code, None)
