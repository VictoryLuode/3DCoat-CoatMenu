"""
Hotkey Editor - Conflict Resolution Dialog

Dialog for resolving hotkey conflicts interactively.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .qt_imports import (
    HAS_QT,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QScrollArea,
    QWidget,
    QMessageBox,
    Qt,
)
from .styles import (
    ICON_GARBAGE,
    RESOLUTION_KEEP,
    RESOLUTION_UNMAP,
    RESOLUTION_DELETE,
    RESOLUTION_REMAP,
    RESOLUTION_GARBAGE,
    DEFAULT_GARBAGE_KEY,
    DEFAULT_GARBAGE_CTRL,
    DEFAULT_GARBAGE_ALT,
    DEFAULT_GARBAGE_SHIFT,
)
from .conflict_utils import find_conflicts_with_global, is_garbage_key

if TYPE_CHECKING:
    from ..hotkey_utils import HotkeyEntry, HotkeysFile


if HAS_QT:
    from .key_capture_dialog import KeyCaptureDialog

    class ConflictResolutionDialog(QDialog):
        """Dialog for resolving hotkey conflicts."""

        def __init__(
            self,
            hotkeys_file: "HotkeysFile",
            parent: QWidget | None = None,
            garbage_key: str = DEFAULT_GARBAGE_KEY,
            garbage_ctrl: bool = DEFAULT_GARBAGE_CTRL,
            garbage_alt: bool = DEFAULT_GARBAGE_ALT,
            garbage_shift: bool = DEFAULT_GARBAGE_SHIFT,
        ) -> None:
            super().__init__(parent)
            self._hotkeys_file = hotkeys_file
            self._conflict_groups: dict[str, list["HotkeyEntry"]] = {}
            self._changes_made: bool = False

            # Garbage key configuration
            self._garbage_key = garbage_key
            self._garbage_ctrl = garbage_ctrl
            self._garbage_alt = garbage_alt
            self._garbage_shift = garbage_shift

            # Track resolution state per entry
            self._resolutions: dict[int, tuple[str, tuple | None]] = {}
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
                "Each group shows commands sharing the same key binding.\n"
                "Select actions: Keep, Unmap, Delete, Remap, or Garbage Key.\n"
                "Apply processes only non-Keep entries, then recalculates conflicts."
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
            self._btn_apply.clicked.connect(self._apply_resolutions)
            button_layout.addWidget(self._btn_apply)

            self._btn_commit = QPushButton("✅ Apply && Close")
            self._btn_commit.setObjectName("successBtn")
            self._btn_commit.clicked.connect(self._apply_and_close)
            button_layout.addWidget(self._btn_commit)

            btn_cancel = QPushButton("Cancel")
            btn_cancel.clicked.connect(self.reject)
            button_layout.addWidget(btn_cancel)

            layout.addLayout(button_layout)

        def _refresh_conflicts(self) -> None:
            """Recalculate conflicts and rebuild the UI."""
            self._resolutions.clear()
            self._entry_widgets.clear()

            self._conflict_groups = find_conflicts_with_global(
                self._hotkeys_file,
                self._garbage_key, self._garbage_ctrl,
                self._garbage_alt, self._garbage_shift
            )

            # Initialize all entries to "keep" by default
            for entries in self._conflict_groups.values():
                for entry in entries:
                    self._resolutions[id(entry)] = (RESOLUTION_KEEP, None)

            self._rebuild_groups_ui()
            self._update_status()

        def _rebuild_groups_ui(self) -> None:
            """Rebuild the conflict group widgets."""
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
            parts = binding_key.split("|")
            room_part = parts[0] if parts[0] else "(Global)"
            key = parts[1] if len(parts) > 1 else "?"

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

            group_entry_ids = [id(e) for e in entries]

            for entry in entries:
                entry_widget = self._create_entry_row(entry, group_entry_ids)
                layout.addWidget(entry_widget)

            return group

        def _create_entry_row(
            self, entry: "HotkeyEntry", group_entry_ids: list[int]
        ) -> QWidget:
            """Create a row widget for a single entry."""
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 4, 0, 4)
            layout.setSpacing(8)

            # Command info
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
            combo.addItem(f"{ICON_GARBAGE} Garbage Key", RESOLUTION_GARBAGE)
            combo.setMinimumWidth(150)

            remap_label = QLabel("")
            remap_label.setStyleSheet("color: #90caf9; font-size: 10px;")
            remap_label.setVisible(False)

            status_label = QLabel("")
            status_label.setMinimumWidth(30)

            entry_id = id(entry)
            self._entry_widgets[entry_id] = {
                "combo": combo,
                "remap_label": remap_label,
                "status_label": status_label,
                "entry": entry,
                "group_ids": group_entry_ids,
            }

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
                remap_binding = self._prompt_remap(entry)
                if remap_binding:
                    self._resolutions[entry_id] = (
                        RESOLUTION_REMAP, remap_binding)
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
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                    combo.blockSignals(False)
                    self._resolutions[entry_id] = (RESOLUTION_KEEP, None)
                    remap_label.setVisible(False)
            elif action == RESOLUTION_GARBAGE:
                garbage_binding = (
                    self._garbage_key,
                    self._garbage_ctrl,
                    self._garbage_alt,
                    self._garbage_shift,
                )
                self._resolutions[entry_id] = (
                    RESOLUTION_GARBAGE, garbage_binding)
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
            """Prompt user to enter a new key binding."""
            while True:
                dialog = KeyCaptureDialog(self, [entry])
                if dialog.exec() != QDialog.Accepted:
                    return None

                new_binding = dialog.get_binding()
                code, ctrl, alt, shift = new_binding

                if code == "key_00":
                    QMessageBox.information(
                        self, "Empty Binding",
                        "You entered an empty binding. Use 'Unmap' instead."
                    )
                    continue

                conflicts = self._check_binding_conflicts(
                    entry, code, ctrl, alt, shift)
                if not conflicts:
                    return new_binding

                conflict_list = "\n".join(
                    f"  • {e.id} ({e.room or 'Global'})" for e in conflicts[:5]
                )
                if len(conflicts) > 5:
                    conflict_list += f"\n  ... and {len(conflicts) - 5} more"

                reply = QMessageBox.warning(
                    self, "Binding Conflict",
                    f"This binding conflicts with:\n{conflict_list}\n\nTry a different key?",
                    QMessageBox.Retry | QMessageBox.Cancel,
                )
                if reply != QMessageBox.Retry:
                    return None

        def _check_binding_conflicts(
            self, entry: "HotkeyEntry", code: str, ctrl: bool, alt: bool, shift: bool
        ) -> list["HotkeyEntry"]:
            """Check if a binding would conflict with any other entry."""
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

                if other.room == entry_room:
                    conflicts.append(other)
                elif other.room == "" or entry_room == "":
                    conflicts.append(other)

            # Check pending remaps
            for eid, (action, remap) in self._resolutions.items():
                if action == RESOLUTION_REMAP and remap and eid != id(entry):
                    r_code, r_ctrl, r_alt, r_shift = remap
                    if r_code == code and r_ctrl == ctrl and r_alt == alt and r_shift == shift:
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

            # Count entries with non-Keep resolutions
            pending_changes = sum(
                1 for action, _ in self._resolutions.values()
                if action != RESOLUTION_KEEP
            )

            for entries in self._conflict_groups.values():
                keep_count = sum(
                    1 for e in entries
                    if self._resolutions.get(id(e), (RESOLUTION_KEEP, None))[0] == RESOLUTION_KEEP
                )
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
                if pending_changes > 0:
                    self._status_label.setText(
                        f"⚠️ {unresolved_groups}/{total_groups} group(s) need resolution. "
                        f"{pending_changes} pending change(s) can be applied."
                    )
                else:
                    self._status_label.setText(
                        f"⚠️ {unresolved_groups}/{total_groups} group(s) need resolution. "
                        f"Select actions for entries (keep, unmap, delete, remap, garbage)."
                    )
                self._status_label.setStyleSheet(
                    "color: #ffb74d; font-size: 12px;")
                self._btn_commit.setEnabled(False)
                self._btn_apply.setEnabled(pending_changes > 0)

        def _update_entry_statuses(self) -> None:
            """Update status indicators on all entry rows."""
            for entries in self._conflict_groups.values():
                keep_count = sum(
                    1 for e in entries
                    if self._resolutions.get(id(e), (RESOLUTION_KEEP, None))[0] == RESOLUTION_KEEP
                )

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
                            status_label.setToolTip("")
                        else:
                            status_label.setText("⚠️")
                            status_label.setStyleSheet("color: #ffb74d;")
                            status_label.setToolTip(
                                f"{keep_count} entries set to 'Keep' - only 1 allowed"
                            )
                    elif action == RESOLUTION_REMAP and remap:
                        conflicts = self._check_binding_conflicts(
                            entry, remap[0], remap[1], remap[2], remap[3]
                        )
                        if conflicts:
                            status_label.setText("⚠️")
                            status_label.setStyleSheet("color: #ef5350;")
                            status_label.setToolTip("Remap still conflicts!")
                        else:
                            status_label.setText("→")
                            status_label.setStyleSheet("color: #90caf9;")
                            status_label.setToolTip("")
                    else:
                        status_label.setText("")
                        status_label.setToolTip("")

        def _apply_resolutions(self) -> None:
            """Apply partial resolutions: only apply changes to entries not set to 'Keep'."""
            changes = 0
            entries_to_delete: list[int] = []
            skipped_keep = 0

            for entry_id, (action, remap) in self._resolutions.items():
                # Skip entries set to "Keep"
                if action == RESOLUTION_KEEP:
                    skipped_keep += 1
                    continue

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
                    entry.code, entry.ctrl, entry.alt, entry.shift = remap
                    changes += 1

            if entries_to_delete:
                self._hotkeys_file.entries = [
                    e for e in self._hotkeys_file.entries
                    if id(e) not in entries_to_delete
                ]

            if changes > 0:
                self._changes_made = True

            self._refresh_conflicts()

            if changes == 0:
                msg = "No changes to apply.\n"
                if skipped_keep > 0:
                    msg += f"All {skipped_keep} selected entries are set to 'Keep'."
                QMessageBox.information(self, "No Changes", msg)
            else:
                QMessageBox.information(
                    self, "Resolutions Applied",
                    f"Applied {changes} resolution(s).\n"
                    f"Skipped {skipped_keep} 'Keep' entries.\n"
                    f"Remaining conflicts: {len(self._conflict_groups)}"
                )

        def _apply_and_close(self) -> None:
            """Apply resolutions and close the dialog."""
            self._apply_resolutions()
            if not self._conflict_groups:
                self.accept()

        def has_changes(self) -> bool:
            """Check if any changes were made."""
            return self._changes_made
