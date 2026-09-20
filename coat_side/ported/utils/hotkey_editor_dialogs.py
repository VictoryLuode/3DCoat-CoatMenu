"""
Hotkey Editor - Dialog Classes

KeyCaptureDialog and ConflictResolutionDialog for the hotkey editor.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from PySide6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QLineEdit,
        QComboBox,
        QDialogButtonBox,
        QGroupBox,
        QScrollArea,
        QWidget,
        QCheckBox,
        QMessageBox,
    )
    from PySide6.QtCore import Qt, QEvent
    from PySide6.QtGui import QKeyEvent

    HAS_QT: bool = True
except ImportError:
    HAS_QT = False
    QDialog = object  # Fallback

if TYPE_CHECKING:
    from ported.utils.hotkey_utils import HotkeyEntry, HotkeysFile

from ported.utils.hotkey_editor_styles import (
    ICON_GARBAGE,
    RESOLUTION_KEEP,
    RESOLUTION_UNMAP,
    RESOLUTION_DELETE,
    RESOLUTION_REMAP,
    RESOLUTION_GARBAGE,
)


# =============================================================================
# KEY CAPTURE DIALOG
# =============================================================================

if HAS_QT:

    class KeyCaptureDialog(QDialog):
        """
        Dialog for capturing a key binding.

        Shows current binding and allows user to press a new key
        or manually select from dropdowns.
        """

        def __init__(
            self,
            parent: QWidget | None,
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
            instructions = QLabel(
                "Press a key to capture it, or use the controls below.\n"
                "Focus the 'Press Key' area and press your desired key."
            )
            instructions.setWordWrap(True)
            layout.addWidget(instructions)

            # Key capture area
            capture_group = QGroupBox("Key Capture")
            capture_layout = QVBoxLayout(capture_group)

            self._capture_display = QLabel("(none)")
            self._capture_display.setAlignment(Qt.AlignCenter)
            self._capture_display.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 20px; "
                "background-color: #1e1e1e; border: 2px solid #555; border-radius: 4px;"
            )
            self._capture_display.setFocusPolicy(Qt.StrongFocus)
            capture_layout.addWidget(self._capture_display)

            # Capture button
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

        def eventFilter(self, obj, event) -> bool:
            """Capture key presses on the capture button."""
            if obj == self._capture_btn and event.type() == QEvent.KeyPress:
                key_event: QKeyEvent = event
                key = key_event.key()

                # Ignore modifier-only keys
                if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
                    return True

                # Get key name
                key_name = self._key_to_string(key)
                if key_name:
                    self._captured_key = key_name
                    self._key_input.setText(key_name)

                    # Capture modifiers from the key press
                    mods = key_event.modifiers()
                    self._ctrl = bool(mods & Qt.ControlModifier)
                    self._alt = bool(mods & Qt.AltModifier)
                    self._shift = bool(mods & Qt.ShiftModifier)

                    self._ctrl_check.setChecked(self._ctrl)
                    self._alt_check.setChecked(self._alt)
                    self._shift_check.setChecked(self._shift)

                    self._update_display()

                return True

            return super().eventFilter(obj, event)

        def _key_to_string(self, key: int) -> str:
            """Convert Qt key code to string representation."""
            # Common key mappings
            key_map = {
                Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C", Qt.Key_D: "D",
                Qt.Key_E: "E", Qt.Key_F: "F", Qt.Key_G: "G", Qt.Key_H: "H",
                Qt.Key_I: "I", Qt.Key_J: "J", Qt.Key_K: "K", Qt.Key_L: "L",
                Qt.Key_M: "M", Qt.Key_N: "N", Qt.Key_O: "O", Qt.Key_P: "P",
                Qt.Key_Q: "Q", Qt.Key_R: "R", Qt.Key_S: "S", Qt.Key_T: "T",
                Qt.Key_U: "U", Qt.Key_V: "V", Qt.Key_W: "W", Qt.Key_X: "X",
                Qt.Key_Y: "Y", Qt.Key_Z: "Z",
                Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
                Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
                Qt.Key_8: "8", Qt.Key_9: "9",
                Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
                Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
                Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
                Qt.Key_Space: "SPACE", Qt.Key_Return: "RETURN", Qt.Key_Enter: "ENTER",
                Qt.Key_Escape: "ESCAPE", Qt.Key_Tab: "TAB", Qt.Key_Backspace: "BACKSPACE",
                Qt.Key_Delete: "DELETE", Qt.Key_Insert: "INSERT",
                Qt.Key_Home: "HOME", Qt.Key_End: "END",
                Qt.Key_PageUp: "PAGEUP", Qt.Key_PageDown: "PAGEDOWN",
                Qt.Key_Left: "LEFT", Qt.Key_Right: "RIGHT",
                Qt.Key_Up: "UP", Qt.Key_Down: "DOWN",
                Qt.Key_Minus: "MINUS", Qt.Key_Plus: "PLUS", Qt.Key_Equal: "EQUAL",
                Qt.Key_BracketLeft: "LBRACKET", Qt.Key_BracketRight: "RBRACKET",
                Qt.Key_Semicolon: "SEMICOLON", Qt.Key_Apostrophe: "APOSTROPHE",
                Qt.Key_Comma: "COMMA", Qt.Key_Period: "PERIOD",
                Qt.Key_Slash: "SLASH", Qt.Key_Backslash: "BACKSLASH",
                Qt.Key_QuoteLeft: "GRAVE",
            }
            return key_map.get(key, "")

        def _on_modifier_changed(self) -> None:
            """Handle modifier checkbox changes."""
            self._ctrl = self._ctrl_check.isChecked()
            self._alt = self._alt_check.isChecked()
            self._shift = self._shift_check.isChecked()
            self._update_display()

        def _on_key_input_changed(self, text: str) -> None:
            """Handle manual key input changes."""
            self._captured_key = text.strip().upper() if text.strip() else ""
            self._update_display()

        def _on_unmap(self) -> None:
            """Clear the key binding."""
            self._captured_key = "key_00"
            self._ctrl = False
            self._alt = False
            self._shift = False
            self._key_input.setText("")
            self._ctrl_check.setChecked(False)
            self._alt_check.setChecked(False)
            self._shift_check.setChecked(False)
            self._update_display()

        def _update_display(self) -> None:
            """Update the key binding display."""
            if not self._captured_key or self._captured_key == "key_00":
                self._capture_display.setText("(unassigned)")
                self._capture_display.setStyleSheet(
                    "font-size: 18px; font-weight: bold; padding: 20px; "
                    "background-color: #1e1e1e; border: 2px solid #555; "
                    "border-radius: 4px; color: #666;"
                )
            else:
                parts = []
                if self._ctrl:
                    parts.append("Ctrl")
                if self._alt:
                    parts.append("Alt")
                if self._shift:
                    parts.append("Shift")
                parts.append(self._captured_key)

                self._capture_display.setText(" + ".join(parts))
                self._capture_display.setStyleSheet(
                    "font-size: 18px; font-weight: bold; padding: 20px; "
                    "background-color: #1e1e1e; border: 2px solid #90caf9; "
                    "border-radius: 4px; color: #90caf9;"
                )

        def get_binding(self) -> tuple[str, bool, bool, bool]:
            """Get the captured binding as (key_code, ctrl, alt, shift)."""
            key = self._captured_key if self._captured_key else "key_00"
            return (key, self._ctrl, self._alt, self._shift)


# =============================================================================
# CONFLICT RESOLUTION DIALOG
# =============================================================================

if HAS_QT:

    class ConflictResolutionDialog(QDialog):
        """
        Dialog for resolving hotkey conflicts.

        Shows groups of conflicting hotkeys and allows the user to
        select a resolution action for each entry:
        - Keep: Keep this binding (only one per group)
        - Unmap: Clear the key binding but keep the entry
        - Delete: Remove the entry entirely
        - Remap: Change to a different key binding

        Conflicts include:
        - Same key binding in the same room
        - Room-specific bindings that conflict with Global bindings
        """

        def __init__(
            self,
            hotkeys_file: "HotkeysFile",
            parent: QWidget | None = None,
            garbage_key: str = "END",
            garbage_ctrl: bool = True,
            garbage_alt: bool = False,
            garbage_shift: bool = False,
        ) -> None:
            super().__init__(parent)
            self._hotkeys_file: "HotkeysFile" = hotkeys_file
            self._conflict_groups: dict[str, list["HotkeyEntry"]] = {}
            self._changes_made: bool = False

            # Garbage key configuration
            self._garbage_key: str = garbage_key
            self._garbage_ctrl: bool = garbage_ctrl
            self._garbage_alt: bool = garbage_alt
            self._garbage_shift: bool = garbage_shift

            # Track resolution state per entry: entry_id -> (action, remap_binding)
            # remap_binding is (code, ctrl, alt, shift) if action is REMAP
            self._resolutions: dict[int, tuple[str, tuple | None]] = {}

            # Track widgets for updating
            self._entry_widgets: dict[int, dict] = {}

            self._setup_dialog()
            self._build_ui()
            self._refresh_conflicts()

        def _setup_dialog(self) -> None:
            """Configure dialog properties."""
            self.setWindowTitle("Resolve Hotkey Conflicts")
            self.setMinimumSize(800, 600)
            self.resize(900, 700)
            self.setModal(True)

        def _build_ui(self) -> None:
            """Build the dialog UI."""
            layout = QVBoxLayout(self)
            layout.setSpacing(12)

            # Header
            header = QLabel(
                "⚡ Hotkey Conflicts\n"
                "Each group shows commands sharing the same key binding (including Global conflicts).\n"
                "For each entry, select an action. Only ONE entry per group can be 'Keep'."
            )
            header.setWordWrap(True)
            header.setStyleSheet("color: #ffb74d; font-weight: bold;")
            layout.addWidget(header)

            # Status label
            self._status_label = QLabel()
            self._status_label.setStyleSheet("font-size: 12px;")
            layout.addWidget(self._status_label)

            # Scroll area for conflict groups
            from ported.lks_utils.gui_qt.widgets.smooth_scroll_area import QSmoothScrollArea
            scroll = QSmoothScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            self._groups_container = QWidget()
            self._groups_layout = QVBoxLayout(self._groups_container)
            self._groups_layout.setSpacing(12)
            self._groups_layout.setContentsMargins(4, 4, 4, 4)
            scroll.setWidget(self._groups_container)

            layout.addWidget(scroll, 1)

            # Button bar
            button_layout = QHBoxLayout()

            btn_refresh = QPushButton("🔄 Recalculate Conflicts")
            btn_refresh.clicked.connect(self._refresh_conflicts)
            button_layout.addWidget(btn_refresh)

            button_layout.addStretch()

            self._btn_apply = QPushButton("✅ Apply Resolutions")
            self._btn_apply.setObjectName("successBtn")
            self._btn_apply.setToolTip("Apply all selected resolutions")
            self._btn_apply.clicked.connect(self._apply_resolutions)
            button_layout.addWidget(self._btn_apply)

            self._btn_commit = QPushButton("✅ Apply && Close")
            self._btn_commit.setObjectName("successBtn")
            self._btn_commit.setToolTip(
                "Apply resolutions and close (only enabled when all groups resolved)")
            self._btn_commit.clicked.connect(self._apply_and_close)
            button_layout.addWidget(self._btn_commit)

            btn_cancel = QPushButton("Cancel")
            btn_cancel.clicked.connect(self.reject)
            button_layout.addWidget(btn_cancel)

            layout.addLayout(button_layout)

        def _refresh_conflicts(self) -> None:
            """Recalculate conflicts and rebuild the UI."""
            # Clear resolutions
            self._resolutions.clear()
            self._entry_widgets.clear()

            # Find conflicts with global awareness
            self._conflict_groups = self._find_conflicts_with_global()

            # Initialize all entries to "keep" by default (user must change all but one)
            for entries in self._conflict_groups.values():
                for entry in entries:
                    self._resolutions[id(entry)] = (RESOLUTION_KEEP, None)

            # Rebuild group widgets
            self._rebuild_groups_ui()
            self._update_status()

        def _is_garbage_key(self, entry: "HotkeyEntry") -> bool:
            """Check if entry uses the garbage key binding."""
            return (
                entry.code == self._garbage_key and
                entry.ctrl == self._garbage_ctrl and
                entry.alt == self._garbage_alt and
                entry.shift == self._garbage_shift
            )

        def _find_conflicts_with_global(self) -> dict[str, list["HotkeyEntry"]]:
            """
            Find conflicts including Global+Room conflicts.

            A conflict occurs when:
            - Multiple entries share the same binding in the same room
            - A room-specific entry shares a binding with a Global entry
            """
            # Build index: (code, ctrl, alt, shift) -> list of entries
            binding_index: dict[tuple, list["HotkeyEntry"]] = {}

            for entry in self._hotkeys_file.entries:
                if not entry.is_assigned:
                    continue
                if entry.is_duplicate:
                    continue
                # Skip garbage key entries - they're intentionally mapped to unused key
                if self._is_garbage_key(entry):
                    continue

                binding_tuple = (entry.code, entry.ctrl,
                                 entry.alt, entry.shift)
                if binding_tuple not in binding_index:
                    binding_index[binding_tuple] = []
                binding_index[binding_tuple].append(entry)

            # Find conflicts
            conflicts: dict[str, list["HotkeyEntry"]] = {}

            for binding_tuple, entries in binding_index.items():
                if len(entries) < 2:
                    continue

                # Group by room, but Global ("") conflicts with everything
                global_entries = [e for e in entries if e.room == ""]
                room_entries: dict[str, list["HotkeyEntry"]] = {}

                for entry in entries:
                    if entry.room:
                        if entry.room not in room_entries:
                            room_entries[entry.room] = []
                        room_entries[entry.room].append(entry)

                # Check for conflicts
                # 1. Multiple globals = conflict
                if len(global_entries) > 1:
                    key = f"|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
                    if key not in conflicts:
                        conflicts[key] = []
                    conflicts[key].extend(global_entries)

                # 2. Multiple in same room = conflict
                for room, room_list in room_entries.items():
                    if len(room_list) > 1:
                        key = f"{room}|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
                        if key not in conflicts:
                            conflicts[key] = []
                        conflicts[key].extend(room_list)

                # 3. Global + any room-specific = conflict
                if global_entries:
                    for room, room_list in room_entries.items():
                        # Combine global + room entries as a conflict group
                        key = f"{room}+Global|{binding_tuple[0]}|{binding_tuple[1]}|{binding_tuple[2]}|{binding_tuple[3]}"
                        if key not in conflicts:
                            conflicts[key] = []
                        # Add global entries if not already
                        for ge in global_entries:
                            if ge not in conflicts[key]:
                                conflicts[key].append(ge)
                        for re in room_list:
                            if re not in conflicts[key]:
                                conflicts[key].append(re)

            # Filter to only actual conflicts (2+ entries with not all allow_stack)
            filtered: dict[str, list["HotkeyEntry"]] = {}
            for key, group in conflicts.items():
                if len(group) > 1 and not all(e.allow_stack for e in group):
                    # Remove duplicates by id
                    seen_ids = set()
                    unique = []
                    for e in group:
                        if id(e) not in seen_ids:
                            seen_ids.add(id(e))
                            unique.append(e)
                    if len(unique) > 1:
                        filtered[key] = unique

            return filtered

        def _rebuild_groups_ui(self) -> None:
            """Rebuild the conflict group widgets."""
            # Clear existing
            while self._groups_layout.count():
                child = self._groups_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if not self._conflict_groups:
                label = QLabel("✅ No conflicts to resolve.")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("color: #81c784; font-size: 14px;")
                self._groups_layout.addWidget(label)
                self._groups_layout.addStretch()
                return

            for binding_key, entries in self._conflict_groups.items():
                group_widget = self._create_conflict_group(
                    binding_key, entries)
                self._groups_layout.addWidget(group_widget)

            self._groups_layout.addStretch()

        def _create_conflict_group(
            self, binding_key: str, entries: list["HotkeyEntry"]
        ) -> QWidget:
            """Create a widget for a single conflict group."""
            # Parse binding key: "Room|Code|Ctrl|Alt|Shift" or "Room+Global|..."
            parts = binding_key.split("|")
            room_part = parts[0] if parts[0] else "(Global)"
            key = parts[1] if len(parts) > 1 else "?"

            # Build modifier string
            mods = []
            if len(parts) > 2 and parts[2] == "True":
                mods.append("Ctrl")
            if len(parts) > 3 and parts[3] == "True":
                mods.append("Alt")
            if len(parts) > 4 and parts[4] == "True":
                mods.append("Shift")
            mod_str = "+".join(mods) + "+" if mods else ""
            binding_display = f"{mod_str}{key}"

            group = QGroupBox(f"⚡ {binding_display} — {room_part}")
            group.setStyleSheet("QGroupBox { font-weight: bold; }")
            layout = QVBoxLayout(group)
            layout.setSpacing(8)

            # Store group info for validation
            group_entry_ids = [id(e) for e in entries]

            # Entry rows with resolution options
            for entry in entries:
                entry_widget = self._create_entry_row(entry, group_entry_ids)
                layout.addWidget(entry_widget)

            return group

        def _create_entry_row(
            self, entry: "HotkeyEntry", group_entry_ids: list[int]
        ) -> QWidget:
            """Create a row widget for a single entry with resolution options."""
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 4, 0, 4)
            layout.setSpacing(8)

            # Command name + room
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)

            cmd_label = QLabel(f"<b>{entry.id}</b>")
            cmd_label.setStyleSheet("font-family: monospace;")
            info_layout.addWidget(cmd_label)

            room_display = entry.room if entry.room else "(Global)"
            room_label = QLabel(f"Room: {room_display}")
            room_label.setStyleSheet("color: #888; font-size: 10px;")
            info_layout.addWidget(room_label)

            layout.addLayout(info_layout, 1)

            # Resolution combo box
            combo = QComboBox()
            combo.addItem("✓ Keep", RESOLUTION_KEEP)
            combo.addItem("🚫 Unmap", RESOLUTION_UNMAP)
            combo.addItem("🗑️ Delete", RESOLUTION_DELETE)
            combo.addItem("🔄 Remap...", RESOLUTION_REMAP)
            combo.addItem(f"{ICON_GARBAGE} Map to Garbage Key",
                          RESOLUTION_GARBAGE)
            combo.setMinimumWidth(150)

            # Remap display label
            remap_label = QLabel("")
            remap_label.setStyleSheet("color: #90caf9; font-size: 10px;")
            remap_label.setVisible(False)

            # Status indicator
            status_label = QLabel("")
            status_label.setMinimumWidth(30)

            # Store widget refs
            entry_id = id(entry)
            self._entry_widgets[entry_id] = {
                "combo": combo,
                "remap_label": remap_label,
                "status_label": status_label,
                "entry": entry,
                "group_ids": group_entry_ids,
            }

            # Connect combo change
            combo.currentIndexChanged.connect(
                lambda idx, eid=entry_id: self._on_resolution_changed(eid)
            )

            layout.addWidget(combo)
            layout.addWidget(remap_label)
            layout.addWidget(status_label)

            return container

        def _on_resolution_changed(self, entry_id: int) -> None:
            """Handle resolution combo change."""
            widgets = self._entry_widgets.get(entry_id)
            if not widgets:
                return

            combo: QComboBox = widgets["combo"]
            remap_label: QLabel = widgets["remap_label"]
            entry: "HotkeyEntry" = widgets["entry"]

            action = combo.currentData()

            if action == RESOLUTION_REMAP:
                # Open remap dialog
                remap_binding = self._prompt_remap(entry)
                if remap_binding:
                    self._resolutions[entry_id] = (
                        RESOLUTION_REMAP, remap_binding)
                    # Show new binding
                    code, ctrl, alt, shift = remap_binding
                    parts = []
                    if ctrl:
                        parts.append("Ctrl")
                    if alt:
                        parts.append("Alt")
                    if shift:
                        parts.append("Shift")
                    parts.append(code)
                    remap_label.setText(f"→ {'+'.join(parts)}")
                    remap_label.setVisible(True)
                else:
                    # Cancelled, revert to Keep
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                    combo.blockSignals(False)
                    self._resolutions[entry_id] = (RESOLUTION_KEEP, None)
                    remap_label.setVisible(False)
            elif action == RESOLUTION_GARBAGE:
                # Map to garbage key (no confirmation needed)
                garbage_binding = (
                    self._garbage_key,
                    self._garbage_ctrl,
                    self._garbage_alt,
                    self._garbage_shift,
                )
                self._resolutions[entry_id] = (
                    RESOLUTION_GARBAGE, garbage_binding)
                # Show garbage key binding
                parts = []
                if self._garbage_ctrl:
                    parts.append("Ctrl")
                if self._garbage_alt:
                    parts.append("Alt")
                if self._garbage_shift:
                    parts.append("Shift")
                parts.append(self._garbage_key)
                remap_label.setText(f"→ {'+'.join(parts)}")
                remap_label.setVisible(True)
            else:
                self._resolutions[entry_id] = (action, None)
                remap_label.setVisible(False)

            self._update_status()
            self._update_entry_statuses()

        def _prompt_remap(self, entry: "HotkeyEntry") -> tuple | None:
            """
            Prompt user to enter a new key binding.
            Returns (code, ctrl, alt, shift) or None if cancelled.
            Validates that the new binding doesn't conflict.
            """
            while True:
                dialog = KeyCaptureDialog(self, [entry])
                if dialog.exec() != QDialog.Accepted:
                    return None

                new_binding = dialog.get_binding()
                code, ctrl, alt, shift = new_binding

                if code == "key_00":
                    # Empty binding is like unmap
                    QMessageBox.information(
                        self, "Empty Binding",
                        "You entered an empty binding. Use 'Unmap' instead."
                    )
                    continue

                # Check for conflicts with the new binding
                conflicts = self._check_binding_conflicts(
                    entry, code, ctrl, alt, shift
                )

                if not conflicts:
                    return new_binding

                # Show conflict warning
                conflict_list = "\n".join(f"  • {e.id} ({e.room or 'Global'})"
                                          for e in conflicts[:5])
                if len(conflicts) > 5:
                    conflict_list += f"\n  ... and {len(conflicts) - 5} more"

                reply = QMessageBox.warning(
                    self,
                    "Binding Conflict",
                    f"This binding conflicts with:\n{conflict_list}\n\n"
                    "Try a different key?",
                    QMessageBox.Retry | QMessageBox.Cancel,
                )

                if reply != QMessageBox.Retry:
                    return None

        def _check_binding_conflicts(
            self,
            entry: "HotkeyEntry",
            code: str,
            ctrl: bool,
            alt: bool,
            shift: bool,
        ) -> list["HotkeyEntry"]:
            """
            Check if a binding would conflict with any other entry.
            Returns list of conflicting entries (excluding the entry itself).
            """
            conflicts: list["HotkeyEntry"] = []
            entry_room = entry.room

            for other in self._hotkeys_file.entries:
                if id(other) == id(entry):
                    continue
                if not other.is_assigned:
                    continue
                if other.code != code:
                    continue
                if other.ctrl != ctrl or other.alt != alt or other.shift != shift:
                    continue

                # Same binding - check room conflict
                # Conflict if: same room, or one is Global
                if other.room == entry_room:
                    conflicts.append(other)
                elif other.room == "" or entry_room == "":
                    conflicts.append(other)

            # Also check against pending remaps in this dialog
            for eid, (action, remap) in self._resolutions.items():
                if action == RESOLUTION_REMAP and remap and eid != id(entry):
                    r_code, r_ctrl, r_alt, r_shift = remap
                    if r_code == code and r_ctrl == ctrl and r_alt == alt and r_shift == shift:
                        # Find the entry
                        for widgets in self._entry_widgets.values():
                            if id(widgets["entry"]) == eid:
                                other_entry = widgets["entry"]
                                if other_entry.room == entry_room or other_entry.room == "" or entry_room == "":
                                    if other_entry not in conflicts:
                                        conflicts.append(other_entry)

            return conflicts

        def _update_status(self) -> None:
            """Update the overall status display."""
            unresolved_groups = 0
            total_groups = len(self._conflict_groups)

            for binding_key, entries in self._conflict_groups.items():
                keep_count = 0
                for entry in entries:
                    action, _ = self._resolutions.get(
                        id(entry), (RESOLUTION_KEEP, None))
                    if action == RESOLUTION_KEEP:
                        keep_count += 1

                if keep_count != 1:
                    unresolved_groups += 1

            if total_groups == 0:
                self._status_label.setText("✅ No conflicts!")
                self._status_label.setStyleSheet(
                    "color: #81c784; font-size: 12px;")
                self._btn_commit.setEnabled(True)
                self._btn_apply.setEnabled(False)
            elif unresolved_groups == 0:
                self._status_label.setText(
                    f"✅ All {total_groups} conflict group(s) resolved! Ready to apply."
                )
                self._status_label.setStyleSheet(
                    "color: #81c784; font-size: 12px;")
                self._btn_commit.setEnabled(True)
                self._btn_apply.setEnabled(True)
            else:
                self._status_label.setText(
                    f"⚠️ {unresolved_groups}/{total_groups} group(s) need resolution. "
                    f"Each group must have exactly ONE 'Keep'."
                )
                self._status_label.setStyleSheet(
                    "color: #ffb74d; font-size: 12px;")
                self._btn_commit.setEnabled(False)
                self._btn_apply.setEnabled(True)

        def _update_entry_statuses(self) -> None:
            """Update status indicators on all entry rows."""
            # Check each group
            for binding_key, entries in self._conflict_groups.items():
                keep_count = 0
                keep_entries = []
                for entry in entries:
                    action, _ = self._resolutions.get(
                        id(entry), (RESOLUTION_KEEP, None))
                    if action == RESOLUTION_KEEP:
                        keep_count += 1
                        keep_entries.append(entry)

                # Update status labels
                for entry in entries:
                    entry_id = id(entry)
                    widgets = self._entry_widgets.get(entry_id)
                    if not widgets:
                        continue

                    status_label: QLabel = widgets["status_label"]
                    action, remap = self._resolutions.get(
                        entry_id, (RESOLUTION_KEEP, None))

                    if action == RESOLUTION_KEEP:
                        if keep_count == 1:
                            status_label.setText("✓")
                            status_label.setStyleSheet("color: #81c784;")
                        else:
                            status_label.setText("⚠️")
                            status_label.setStyleSheet("color: #ffb74d;")
                            status_label.setToolTip(
                                f"{keep_count} entries set to 'Keep' - only 1 allowed"
                            )
                    elif action == RESOLUTION_REMAP:
                        # Check if remap conflicts
                        if remap:
                            conflicts = self._check_binding_conflicts(
                                entry, remap[0], remap[1], remap[2], remap[3]
                            )
                            if conflicts:
                                status_label.setText("⚠️")
                                status_label.setStyleSheet("color: #ef5350;")
                                status_label.setToolTip(
                                    "Remap still conflicts!")
                            else:
                                status_label.setText("→")
                                status_label.setStyleSheet("color: #90caf9;")
                                status_label.setToolTip("")
                    else:
                        status_label.setText("")
                        status_label.setToolTip("")

        def _apply_resolutions(self) -> None:
            """Apply all selected resolutions without closing."""
            # First validate that all groups are properly resolved
            invalid_groups = []
            for binding_key, entries in self._conflict_groups.items():
                keep_count = 0
                for entry in entries:
                    action, _ = self._resolutions.get(
                        id(entry), (RESOLUTION_KEEP, None))
                    if action == RESOLUTION_KEEP:
                        keep_count += 1

                if keep_count != 1:
                    invalid_groups.append(binding_key)

            if invalid_groups:
                QMessageBox.warning(
                    self,
                    "Cannot Apply Resolutions",
                    f"Cannot apply resolutions: {len(invalid_groups)} conflict group(s) "
                    f"do not have exactly one 'Keep' selected.\n\n"
                    f"Each conflict group must have exactly ONE entry set to 'Keep', "
                    f"and all others must be Unmap, Delete, Remap, or Garbage.",
                )
                return

            changes = 0

            # Process in order: deletes first, then unmaps, then remaps
            entries_to_delete: list[int] = []

            for entry_id, (action, remap) in self._resolutions.items():
                # Find entry
                entry = None
                for e in self._hotkeys_file.entries:
                    if id(e) == entry_id:
                        entry = e
                        break

                if not entry:
                    continue

                if action == RESOLUTION_DELETE:
                    entries_to_delete.append(entry_id)
                    changes += 1
                elif action == RESOLUTION_UNMAP:
                    entry.code = "key_00"
                    entry.ctrl = False
                    entry.alt = False
                    entry.shift = False
                    changes += 1
                elif action == RESOLUTION_REMAP and remap:
                    entry.code, entry.ctrl, entry.alt, entry.shift = remap
                    changes += 1
                elif action == RESOLUTION_GARBAGE and remap:
                    # Map to garbage key
                    entry.code, entry.ctrl, entry.alt, entry.shift = remap
                    changes += 1

            # Delete entries
            if entries_to_delete:
                self._hotkeys_file.entries = [
                    e for e in self._hotkeys_file.entries
                    if id(e) not in entries_to_delete
                ]

            if changes > 0:
                self._changes_made = True

            # Refresh
            self._refresh_conflicts()

            QMessageBox.information(
                self,
                "Resolutions Applied",
                f"Applied {changes} resolution(s).\n"
                f"Remaining conflicts: {len(self._conflict_groups)}"
            )

        def _apply_and_close(self) -> None:
            """Apply resolutions and close the dialog."""
            self._apply_resolutions()
            if not self._conflict_groups:
                self.accept()
            # If there are still conflicts, don't close

        def has_changes(self) -> bool:
            """Check if any changes were made."""
            return self._changes_made
