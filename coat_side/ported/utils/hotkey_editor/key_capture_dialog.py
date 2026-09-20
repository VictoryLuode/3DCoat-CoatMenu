"""
Hotkey Editor - Key Capture Dialog

Dialog for capturing keyboard shortcuts.
Uses keycode_map.py for accurate Qt → 3DCoat XML code conversion.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .qt_imports import (
    HAS_QT,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialogButtonBox,
    QGroupBox,
    QCheckBox,
    Qt,
    QEvent,
)

# Import the authoritative keycode mapping with fallback for standalone mode
try:
    from ..keycode_map import (
        KEY_UNASSIGNED,
        UNMAPPABLE_KEYS,
        COAT_TO_DISPLAY,
        get_display_key,
        normalize_manual_input,
        # Individual key constants for Qt mapping
        KEY_A, KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J,
        KEY_K, KEY_L, KEY_M, KEY_N, KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T,
        KEY_U, KEY_V, KEY_W, KEY_X, KEY_Y, KEY_Z,
        KEY_0, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9,
        KEY_NUM0, KEY_NUM1, KEY_NUM2, KEY_NUM3, KEY_NUM4, KEY_NUM5,
        KEY_NUM6, KEY_NUM7, KEY_NUM8, KEY_NUM9,
        KEY_NUM_DIVIDE, KEY_NUM_MULTIPLY, KEY_NUM_MINUS, KEY_NUM_PLUS, KEY_NUM_DECIMAL,
        KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6,
        KEY_F7, KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12,
        KEY_ENTER, KEY_ESCAPE, KEY_SPACE, KEY_TAB, KEY_BACKSPACE,
        KEY_DELETE, KEY_INSERT, KEY_HOME, KEY_END, KEY_PAGE_UP, KEY_PAGE_DOWN,
        KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT,
        KEY_BACKTICK, KEY_TILDE, KEY_MINUS, KEY_EQUALS, KEY_PLUS,
        KEY_BRACKET_LEFT, KEY_BRACKET_RIGHT, KEY_BACKSLASH,
        KEY_SEMICOLON, KEY_APOSTROPHE, KEY_COMMA, KEY_PERIOD,
        KEY_SLASH, KEY_QUESTION, KEY_LESS_THAN, KEY_GREATER_THAN,
    )
except (ImportError, ModuleNotFoundError):
    # Standalone mode: load keycode_map directly from file
    import importlib.util
    _keycode_map_path = Path(__file__).parent.parent / "keycode_map.py"
    _spec = importlib.util.spec_from_file_location(
        "keycode_map", _keycode_map_path)
    _keycode_map = importlib.util.module_from_spec(_spec)
    sys.modules["keycode_map"] = _keycode_map
    _spec.loader.exec_module(_keycode_map)

    KEY_UNASSIGNED = _keycode_map.KEY_UNASSIGNED
    UNMAPPABLE_KEYS = _keycode_map.UNMAPPABLE_KEYS
    COAT_TO_DISPLAY = _keycode_map.COAT_TO_DISPLAY
    get_display_key = _keycode_map.get_display_key
    normalize_manual_input = _keycode_map.normalize_manual_input
    KEY_A = _keycode_map.KEY_A
    KEY_B = _keycode_map.KEY_B
    KEY_C = _keycode_map.KEY_C
    KEY_D = _keycode_map.KEY_D
    KEY_E = _keycode_map.KEY_E
    KEY_F = _keycode_map.KEY_F
    KEY_G = _keycode_map.KEY_G
    KEY_H = _keycode_map.KEY_H
    KEY_I = _keycode_map.KEY_I
    KEY_J = _keycode_map.KEY_J
    KEY_K = _keycode_map.KEY_K
    KEY_L = _keycode_map.KEY_L
    KEY_M = _keycode_map.KEY_M
    KEY_N = _keycode_map.KEY_N
    KEY_O = _keycode_map.KEY_O
    KEY_P = _keycode_map.KEY_P
    KEY_Q = _keycode_map.KEY_Q
    KEY_R = _keycode_map.KEY_R
    KEY_S = _keycode_map.KEY_S
    KEY_T = _keycode_map.KEY_T
    KEY_U = _keycode_map.KEY_U
    KEY_V = _keycode_map.KEY_V
    KEY_W = _keycode_map.KEY_W
    KEY_X = _keycode_map.KEY_X
    KEY_Y = _keycode_map.KEY_Y
    KEY_Z = _keycode_map.KEY_Z
    KEY_0 = _keycode_map.KEY_0
    KEY_1 = _keycode_map.KEY_1
    KEY_2 = _keycode_map.KEY_2
    KEY_3 = _keycode_map.KEY_3
    KEY_4 = _keycode_map.KEY_4
    KEY_5 = _keycode_map.KEY_5
    KEY_6 = _keycode_map.KEY_6
    KEY_7 = _keycode_map.KEY_7
    KEY_8 = _keycode_map.KEY_8
    KEY_9 = _keycode_map.KEY_9
    KEY_NUM0 = _keycode_map.KEY_NUM0
    KEY_NUM1 = _keycode_map.KEY_NUM1
    KEY_NUM2 = _keycode_map.KEY_NUM2
    KEY_NUM3 = _keycode_map.KEY_NUM3
    KEY_NUM4 = _keycode_map.KEY_NUM4
    KEY_NUM5 = _keycode_map.KEY_NUM5
    KEY_NUM6 = _keycode_map.KEY_NUM6
    KEY_NUM7 = _keycode_map.KEY_NUM7
    KEY_NUM8 = _keycode_map.KEY_NUM8
    KEY_NUM9 = _keycode_map.KEY_NUM9
    KEY_NUM_DIVIDE = _keycode_map.KEY_NUM_DIVIDE
    KEY_NUM_MULTIPLY = _keycode_map.KEY_NUM_MULTIPLY
    KEY_NUM_MINUS = _keycode_map.KEY_NUM_MINUS
    KEY_NUM_PLUS = _keycode_map.KEY_NUM_PLUS
    KEY_NUM_DECIMAL = _keycode_map.KEY_NUM_DECIMAL
    KEY_F1 = _keycode_map.KEY_F1
    KEY_F2 = _keycode_map.KEY_F2
    KEY_F3 = _keycode_map.KEY_F3
    KEY_F4 = _keycode_map.KEY_F4
    KEY_F5 = _keycode_map.KEY_F5
    KEY_F6 = _keycode_map.KEY_F6
    KEY_F7 = _keycode_map.KEY_F7
    KEY_F8 = _keycode_map.KEY_F8
    KEY_F9 = _keycode_map.KEY_F9
    KEY_F10 = _keycode_map.KEY_F10
    KEY_F11 = _keycode_map.KEY_F11
    KEY_F12 = _keycode_map.KEY_F12
    KEY_ENTER = _keycode_map.KEY_ENTER
    KEY_ESCAPE = _keycode_map.KEY_ESCAPE
    KEY_SPACE = _keycode_map.KEY_SPACE
    KEY_TAB = _keycode_map.KEY_TAB
    KEY_BACKSPACE = _keycode_map.KEY_BACKSPACE
    KEY_DELETE = _keycode_map.KEY_DELETE
    KEY_INSERT = _keycode_map.KEY_INSERT
    KEY_HOME = _keycode_map.KEY_HOME
    KEY_END = _keycode_map.KEY_END
    KEY_PAGE_UP = _keycode_map.KEY_PAGE_UP
    KEY_PAGE_DOWN = _keycode_map.KEY_PAGE_DOWN
    KEY_UP = _keycode_map.KEY_UP
    KEY_DOWN = _keycode_map.KEY_DOWN
    KEY_LEFT = _keycode_map.KEY_LEFT
    KEY_RIGHT = _keycode_map.KEY_RIGHT
    KEY_BACKTICK = _keycode_map.KEY_BACKTICK
    KEY_TILDE = _keycode_map.KEY_TILDE
    KEY_MINUS = _keycode_map.KEY_MINUS
    KEY_EQUALS = _keycode_map.KEY_EQUALS
    KEY_PLUS = _keycode_map.KEY_PLUS
    KEY_BRACKET_LEFT = _keycode_map.KEY_BRACKET_LEFT
    KEY_BRACKET_RIGHT = _keycode_map.KEY_BRACKET_RIGHT
    KEY_BACKSLASH = _keycode_map.KEY_BACKSLASH
    KEY_SEMICOLON = _keycode_map.KEY_SEMICOLON
    KEY_APOSTROPHE = _keycode_map.KEY_APOSTROPHE
    KEY_COMMA = _keycode_map.KEY_COMMA
    KEY_PERIOD = _keycode_map.KEY_PERIOD
    KEY_SLASH = _keycode_map.KEY_SLASH
    KEY_QUESTION = _keycode_map.KEY_QUESTION
    KEY_LESS_THAN = _keycode_map.KEY_LESS_THAN
    KEY_GREATER_THAN = _keycode_map.KEY_GREATER_THAN

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from PySide6.QtGui import QKeyEvent
    from ..hotkey_utils import HotkeyEntry

# =============================================================================
# Qt Key → 3DCoat XML Code Mapping
# =============================================================================
# Maps Qt.Key_* constants directly to 3DCoat's XML code values.
# This uses the verified constants from keycode_map.py.
# None = key is unmappable in 3DCoat.

_QT_TO_COAT: dict[int, str | None] = {}

if HAS_QT:
    _QT_TO_COAT = {
        # Letters (A-Z) → uppercase single char
        Qt.Key_A: KEY_A, Qt.Key_B: KEY_B, Qt.Key_C: KEY_C, Qt.Key_D: KEY_D,
        Qt.Key_E: KEY_E, Qt.Key_F: KEY_F, Qt.Key_G: KEY_G, Qt.Key_H: KEY_H,
        Qt.Key_I: KEY_I, Qt.Key_J: KEY_J, Qt.Key_K: KEY_K, Qt.Key_L: KEY_L,
        Qt.Key_M: KEY_M, Qt.Key_N: KEY_N, Qt.Key_O: KEY_O, Qt.Key_P: KEY_P,
        Qt.Key_Q: KEY_Q, Qt.Key_R: KEY_R, Qt.Key_S: KEY_S, Qt.Key_T: KEY_T,
        Qt.Key_U: KEY_U, Qt.Key_V: KEY_V, Qt.Key_W: KEY_W, Qt.Key_X: KEY_X,
        Qt.Key_Y: KEY_Y, Qt.Key_Z: KEY_Z,

        # Numbers (top row) → single digit char
        Qt.Key_0: KEY_0, Qt.Key_1: KEY_1, Qt.Key_2: KEY_2, Qt.Key_3: KEY_3,
        Qt.Key_4: KEY_4, Qt.Key_5: KEY_5, Qt.Key_6: KEY_6, Qt.Key_7: KEY_7,
        Qt.Key_8: KEY_8, Qt.Key_9: KEY_9,

        # Function keys → "F1" through "F12"
        Qt.Key_F1: KEY_F1, Qt.Key_F2: KEY_F2, Qt.Key_F3: KEY_F3, Qt.Key_F4: KEY_F4,
        Qt.Key_F5: KEY_F5, Qt.Key_F6: KEY_F6, Qt.Key_F7: KEY_F7, Qt.Key_F8: KEY_F8,
        Qt.Key_F9: KEY_F9, Qt.Key_F10: KEY_F10, Qt.Key_F11: KEY_F11, Qt.Key_F12: KEY_F12,

        # Special keys - NOTE: 3DCoat uses inconsistent naming!
        Qt.Key_Space: KEY_SPACE,       # "SPACE"
        Qt.Key_Return: KEY_ENTER,      # "ENTER" (main keyboard)
        # "ENTER" (numpad - same as Return in 3DCoat)
        Qt.Key_Enter: KEY_ENTER,
        Qt.Key_Escape: KEY_ESCAPE,     # "ESC"
        Qt.Key_Tab: KEY_TAB,           # "Tab" (mixed case!)
        Qt.Key_Backspace: KEY_BACKSPACE,  # None - UNMAPPABLE
        Qt.Key_Delete: KEY_DELETE,     # "DELETE"
        Qt.Key_Insert: KEY_INSERT,     # "INS" (abbreviated!)
        Qt.Key_Home: KEY_HOME,         # "HOME"
        Qt.Key_End: KEY_END,           # None - UNMAPPABLE
        Qt.Key_PageUp: KEY_PAGE_UP,    # "PGUP"
        Qt.Key_PageDown: KEY_PAGE_DOWN,  # "PGDN"

        # Arrow keys - Capitalized names
        Qt.Key_Up: KEY_UP,       # "Up"
        Qt.Key_Down: KEY_DOWN,   # "Down"
        Qt.Key_Left: KEY_LEFT,   # "Left"
        Qt.Key_Right: KEY_RIGHT,  # "Right"

        # Symbol keys - literal storage
        Qt.Key_QuoteLeft: KEY_BACKTICK,      # "`"
        Qt.Key_AsciiTilde: KEY_TILDE,        # "~"
        Qt.Key_Minus: KEY_MINUS,             # "-"
        Qt.Key_Equal: KEY_EQUALS,            # "="
        Qt.Key_Plus: KEY_PLUS,               # "+"
        Qt.Key_BracketLeft: KEY_BRACKET_LEFT,   # "["
        Qt.Key_BracketRight: KEY_BRACKET_RIGHT,  # "]"
        Qt.Key_Backslash: KEY_BACKSLASH,     # "key_DC" (scancode!)
        Qt.Key_Semicolon: KEY_SEMICOLON,     # ";"
        Qt.Key_Apostrophe: KEY_APOSTROPHE,   # "'"
        Qt.Key_Slash: KEY_SLASH,             # "/"
        Qt.Key_Question: KEY_QUESTION,       # "?"

        # CRITICAL: Period and Comma use shifted-character storage!
        # 3DCoat stores ">" for both . and > (Shift distinguishes)
        # 3DCoat stores "<" for both , and < (Shift distinguishes)
        Qt.Key_Period: KEY_PERIOD,   # "&gt" - displayed as "." when Shift=false
        Qt.Key_Comma: KEY_COMMA,     # "&lt" - displayed as "," when Shift=false
        Qt.Key_Less: KEY_LESS_THAN,  # "&lt" - displayed as "<" when Shift=true
        Qt.Key_Greater: KEY_GREATER_THAN,  # "&gt" - displayed as ">" when Shift=true
    }

    # =============================================================================
    # Numpad keys - separate mapping (Qt may report differently based on NumLock)
    # =============================================================================
    # Note: Qt uses same Key_0-9 for numpad digits when NumLock is on,
    # but we can detect numpad via keypad modifier.
    # For explicit numpad handling, we'd need to check event.modifiers() & Qt.KeypadModifier

    _NUMPAD_TO_COAT: dict[int, str | None] = {
        # When KeypadModifier is set, these are the codes
        Qt.Key_0: KEY_NUM0, Qt.Key_1: KEY_NUM1, Qt.Key_2: KEY_NUM2,
        Qt.Key_3: KEY_NUM3, Qt.Key_4: KEY_NUM4, Qt.Key_5: KEY_NUM5,
        Qt.Key_6: KEY_NUM6, Qt.Key_7: KEY_NUM7, Qt.Key_8: KEY_NUM8,
        Qt.Key_9: KEY_NUM9,
        Qt.Key_Slash: KEY_NUM_DIVIDE,     # "NUM/"
        Qt.Key_Asterisk: KEY_NUM_MULTIPLY,  # "NUM*"
        Qt.Key_Minus: KEY_NUM_MINUS,      # "NUM_MINUS"
        Qt.Key_Plus: KEY_NUM_PLUS,        # "NUM_PLUS"
        Qt.Key_Period: KEY_NUM_DECIMAL,   # "key_6E" (scancode!)
        # Numpad Enter is unmappable - 3DCoat doesn't distinguish from main Enter
    }


if HAS_QT:

    class KeyCaptureDialog(QDialog):
        """Dialog for capturing a key binding."""

        def __init__(
            self,
            parent: "QWidget | None",
            entries: list["HotkeyEntry"],
        ) -> None:
            super().__init__(parent)
            self._entries = entries
            self._captured_key: str = ""
            self._ctrl: bool = False
            self._alt: bool = False
            self._shift: bool = False

            # Initialize from first entry if single
            if len(entries) == 1:
                entry = entries[0]
                self._captured_key = entry.code if entry.is_assigned else ""
                self._ctrl = entry.ctrl
                self._alt = entry.alt
                self._shift = entry.shift

            self._setup_dialog()
            self._build_ui()
            self._update_display()

        def _setup_dialog(self) -> None:
            """Configure dialog properties."""
            count = len(self._entries)
            title = "Edit Key Binding"
            if count > 1:
                title += f" ({count} entries)"
            self.setWindowTitle(title)
            self.setMinimumWidth(350)
            self.setModal(True)

        def _build_ui(self) -> None:
            """Build the dialog UI."""
            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Instructions
            layout.addWidget(QLabel(
                "Press a key to capture it, or use the controls below.\n"
                "Focus the 'Press Key' area and press your desired key."
            ))

            # Key capture area
            capture_group = QGroupBox("Key Capture")
            capture_layout = QVBoxLayout(capture_group)

            self._capture_display = QLabel("(none)")
            self._capture_display.setAlignment(Qt.AlignCenter)
            self._style_display_inactive()
            self._capture_display.setFocusPolicy(Qt.StrongFocus)
            capture_layout.addWidget(self._capture_display)

            self._capture_btn = QPushButton(
                "🎯 Click here, then press a key...")
            self._capture_btn.setFocusPolicy(Qt.StrongFocus)
            self._capture_btn.setMinimumHeight(40)
            self._capture_btn.installEventFilter(self)
            capture_layout.addWidget(self._capture_btn)

            layout.addWidget(capture_group)

            # Modifier checkboxes
            mod_group = QGroupBox("Modifiers")
            mod_layout = QHBoxLayout(mod_group)

            self._ctrl_check = QCheckBox("Ctrl")
            self._ctrl_check.setChecked(self._ctrl)
            self._ctrl_check.stateChanged.connect(self._on_modifier_changed)
            mod_layout.addWidget(self._ctrl_check)

            self._alt_check = QCheckBox("Alt")
            self._alt_check.setChecked(self._alt)
            self._alt_check.stateChanged.connect(self._on_modifier_changed)
            mod_layout.addWidget(self._alt_check)

            self._shift_check = QCheckBox("Shift")
            self._shift_check.setChecked(self._shift)
            self._shift_check.stateChanged.connect(self._on_modifier_changed)
            mod_layout.addWidget(self._shift_check)

            layout.addWidget(mod_group)

            # Manual key entry
            manual_group = QGroupBox("Manual Entry")
            manual_layout = QHBoxLayout(manual_group)

            manual_layout.addWidget(QLabel("Key code:"))
            self._key_input = QLineEdit()
            self._key_input.setPlaceholderText("e.g., A, F1, SPACE, ESCAPE")
            if self._captured_key and self._captured_key != "key_00":
                self._key_input.setText(self._captured_key)
            self._key_input.textChanged.connect(self._on_key_input_changed)
            manual_layout.addWidget(self._key_input, 1)

            layout.addWidget(manual_group)

            # Unmap button
            unmap_btn = QPushButton("🚫 Unmap (Clear Binding)")
            unmap_btn.clicked.connect(self._on_unmap)
            layout.addWidget(unmap_btn)

            # Button bar
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

        def _style_display_inactive(self) -> None:
            """Style the display for unassigned state."""
            self._capture_display.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 20px; "
                "background-color: #1e1e1e; border: 2px solid #555; "
                "border-radius: 4px; color: #666;"
            )

        def _style_display_active(self) -> None:
            """Style the display for assigned state."""
            self._capture_display.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 20px; "
                "background-color: #1e1e1e; border: 2px solid #90caf9; "
                "border-radius: 4px; color: #90caf9;"
            )

        def eventFilter(self, obj, event) -> bool:
            """Capture key presses on the capture button."""
            if obj == self._capture_btn and event.type() == QEvent.KeyPress:
                key = event.key()

                # Ignore modifier-only keys
                if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
                    return True

                mods = event.modifiers()
                is_numpad = bool(mods & Qt.KeypadModifier)

                # Get the 3DCoat XML code for this key
                if is_numpad and key in _NUMPAD_TO_COAT:
                    coat_code = _NUMPAD_TO_COAT.get(key)
                else:
                    coat_code = _QT_TO_COAT.get(key)

                # Check if key is unmappable
                if coat_code is None:
                    # Show warning but don't capture
                    self._capture_display.setText(
                        "⛔ Key not mappable in 3DCoat")
                    self._capture_display.setStyleSheet(
                        "font-size: 18px; font-weight: bold; padding: 20px; "
                        "background-color: #1e1e1e; border: 2px solid #ff5252; "
                        "border-radius: 4px; color: #ff5252;"
                    )
                    return True

                if coat_code:
                    self._captured_key = coat_code
                    # Show display-friendly version in manual input
                    display_text = get_display_key(
                        coat_code, bool(mods & Qt.ShiftModifier))
                    self._key_input.setText(display_text)

                    self._ctrl = bool(mods & Qt.ControlModifier)
                    self._alt = bool(mods & Qt.AltModifier)
                    self._shift = bool(mods & Qt.ShiftModifier)

                    self._ctrl_check.setChecked(self._ctrl)
                    self._alt_check.setChecked(self._alt)
                    self._shift_check.setChecked(self._shift)

                    self._update_display()

                return True

            return super().eventFilter(obj, event)

        def _on_modifier_changed(self) -> None:
            """Handle modifier checkbox changes."""
            self._ctrl = self._ctrl_check.isChecked()
            self._alt = self._alt_check.isChecked()
            self._shift = self._shift_check.isChecked()
            self._update_display()

        def _on_key_input_changed(self, text: str) -> None:
            """Handle manual key input changes."""
            if not text.strip():
                self._captured_key = ""
            else:
                # Normalize the input to valid 3DCoat XML code
                self._captured_key = normalize_manual_input(text)
            self._update_display()

        def _on_unmap(self) -> None:
            """Clear the key binding."""
            self._captured_key = KEY_UNASSIGNED
            self._ctrl = False
            self._alt = False
            self._shift = False
            self._key_input.setText("")
            self._ctrl_check.setChecked(False)
            self._alt_check.setChecked(False)
            self._shift_check.setChecked(False)
            self._update_display()

        def _update_display(self) -> None:
            """Update the key binding display using proper display names."""
            if not self._captured_key or self._captured_key == KEY_UNASSIGNED:
                self._capture_display.setText("(unassigned)")
                self._style_display_inactive()
            else:
                parts: list[str] = []
                if self._ctrl:
                    parts.append("Ctrl")
                if self._alt:
                    parts.append("Alt")
                if self._shift:
                    parts.append("Shift")

                # Use get_display_key for human-readable key name
                # This handles the . / , / < / > special cases correctly
                display_key = get_display_key(self._captured_key, self._shift)
                parts.append(display_key)

                self._capture_display.setText(" + ".join(parts))
                self._style_display_active()

        def get_binding(self) -> tuple[str, bool, bool, bool]:
            """Get the captured binding as (coat_xml_code, ctrl, alt, shift)."""
            key = self._captured_key if self._captured_key else KEY_UNASSIGNED
            return (key, self._ctrl, self._alt, self._shift)
