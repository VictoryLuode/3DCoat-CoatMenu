"""
Hotkey Editor - Main Window

The primary editor window for managing 3DCoat hotkey bindings.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .qt_imports import (
    HAS_QT,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QStatusBar,
    QFrame,
    QSplitter,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QScrollArea,
    QFormLayout,
    QCheckBox,
    QIcon,
    Qt,
    QColor,
    QBrush,
    QAction,
    QPixmap,
    QPainter,
)
from PySide6.QtSvg import QSvgRenderer
from .styles import (
    EDITOR_STYLESHEET,
    COL_COMMAND,
    COL_KEY,
    COL_MODIFIERS,
    COL_ROOM,
    COL_STATUS,
    COL_USER_DEF,
    COL_STACKABLE,
    DEFAULT_GARBAGE_KEY,
    DEFAULT_GARBAGE_CTRL,
    DEFAULT_GARBAGE_ALT,
    DEFAULT_GARBAGE_SHIFT,
    COLOR_DUPLICATE,
    COLOR_CONFLICT,
    COLOR_ORPHAN,
    COLOR_NORMAL,
    COLOR_UNASSIGNED,
    COLOR_GARBAGE,
    ICON_DUPLICATE,
    ICON_CONFLICT,
    ICON_ORPHAN,
    ICON_GARBAGE,
    ICON_OK,
)
# SVG icon paths for file toolbar buttons — pre-colored with theme accent
from pathlib import Path as _Path
_ICONS_DIR = _Path(__file__).resolve().parent.parent.parent / 'ported.utils' / 'ui' / 'data'

def _make_colored_icon(name: str, color: str, size: int = 16) -> QIcon:
    svg_path: Path = _ICONS_DIR / f"{name}.svg"
    content: str = svg_path.read_text(encoding="utf-8")
    content = content.replace("currentColor", color)
    renderer: QSvgRenderer = QSvgRenderer(content.encode("utf-8"))
    pixmap: QPixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter: QPainter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

try:
    from ported.utils.ui.styles import COLOR_ACCENT
except ImportError:
    COLOR_ACCENT = "#90caf9"

_ICON_OPEN = _make_colored_icon('load', COLOR_ACCENT)
_ICON_SAVE_ICON = _make_colored_icon('save', COLOR_ACCENT)
_ICON_SAVE_AS_ICON = _make_colored_icon('save_as', COLOR_ACCENT)

from .hotkey_imports import (
    HotkeyEntry,
    HotkeysFile,
    VALID_ROOMS,
    parse_hotkeys_file,
    validate_all,
    remove_duplicates,
    remove_orphan_rooms,
    create_backup,
    list_backups,
    restore_backup,
    save_hotkeys_file,
    get_stats,
    discover_hotkeys_path,
)
from .conflict_utils import count_conflicts

if TYPE_CHECKING:
    from ..hotkey_utils import HotkeyStats


if HAS_QT:
    from .key_capture_dialog import KeyCaptureDialog
    from .conflict_resolution_dialog import ConflictResolutionDialog

    class HotkeyEditorWindow(QMainWindow):
        """Main window for the hotkey editor."""

        def __init__(
            self,
            hotkeys_path: Path | None = None,
            parent: QWidget | None = None,
        ) -> None:
            super().__init__(parent)
            self._hotkeys_path: Path | None = hotkeys_path
            self._hotkeys_file: HotkeysFile | None = None

            # Garbage key settings
            self._garbage_key: str = DEFAULT_GARBAGE_KEY
            self._garbage_ctrl: bool = DEFAULT_GARBAGE_CTRL
            self._garbage_alt: bool = DEFAULT_GARBAGE_ALT
            self._garbage_shift: bool = DEFAULT_GARBAGE_SHIFT

            # UI state
            self._current_room_filter: str = "All"
            self._current_filter_text: str = ""
            self._show_only_issues: bool = False

            self._setup_window()
            self._build_ui()

            if hotkeys_path:
                self._load_file(hotkeys_path)
            else:
                # Try to auto-detect
                detected = discover_hotkeys_path()
                if detected:
                    self._load_file(detected)

        def _setup_window(self) -> None:
            """Configure window properties."""
            self.setWindowTitle("🎹 LKS Hotkey Editor")
            self.setMinimumSize(1200, 700)
            self.resize(1400, 800)
            self.setStyleSheet(EDITOR_STYLESHEET)

        def _build_ui(self) -> None:
            """Build the main UI."""
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(8)

            # Top toolbar
            toolbar = self._create_toolbar()
            layout.addWidget(toolbar)

            # File controls
            file_row = self._create_file_controls()
            layout.addWidget(file_row)

            # Filter bar
            filter_row = self._create_filter_bar()
            layout.addWidget(filter_row)

            # Main content (splitter with table + sidebar)
            splitter = QSplitter(Qt.Horizontal)

            # Table
            self._table = self._create_table()
            splitter.addWidget(self._table)

            # Sidebar
            sidebar = self._create_sidebar()
            splitter.addWidget(sidebar)

            splitter.setSizes([900, 300])
            layout.addWidget(splitter, 1)

            # Status bar
            self._status_bar = QStatusBar()
            self.setStatusBar(self._status_bar)
            self._status_bar.showMessage("Ready")

        def _create_toolbar(self) -> QWidget:
            """Create the action toolbar."""
            toolbar = QWidget()
            layout = QHBoxLayout(toolbar)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            # Cleanup actions
            layout.addWidget(QLabel("🧹 Cleanup:"))

            btn_remove_dups = QPushButton("Remove Duplicates")
            btn_remove_dups.setToolTip(
                "Remove duplicate command entries (keeps first)")
            btn_remove_dups.clicked.connect(self._on_remove_duplicates)
            layout.addWidget(btn_remove_dups)

            btn_remove_orphans = QPushButton("Remove Orphan Rooms")
            btn_remove_orphans.setToolTip(
                "Remove entries with invalid room names")
            btn_remove_orphans.clicked.connect(self._on_remove_orphans)
            layout.addWidget(btn_remove_orphans)

            btn_remove_unassigned = QPushButton("Remove Unassigned")
            btn_remove_unassigned.setToolTip(
                "Remove entries with no key binding")
            btn_remove_unassigned.clicked.connect(self._on_remove_unassigned)
            layout.addWidget(btn_remove_unassigned)

            layout.addWidget(self._create_separator())

            # Conflict resolution
            layout.addWidget(QLabel("⚡ Conflicts:"))

            btn_resolve = QPushButton("Resolve Conflicts...")
            btn_resolve.setToolTip(
                "Open dialog to resolve key binding conflicts")
            btn_resolve.clicked.connect(self._on_resolve_conflicts)
            layout.addWidget(btn_resolve)

            layout.addStretch()

            return toolbar

        def _create_file_controls(self) -> QWidget:
            """Create file open/save controls."""
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            layout.addWidget(QLabel("📁 File:"))

            self._file_label = QLabel("(no file loaded)")
            self._file_label.setStyleSheet("color: #888;")
            layout.addWidget(self._file_label, 1)

            btn_open = QPushButton("Open...")
            btn_open.setIcon(_ICON_OPEN)
            btn_open.clicked.connect(self._on_open_file)
            layout.addWidget(btn_open)

            btn_save = QPushButton("Save")
            btn_save.setIcon(_ICON_SAVE_ICON)
            btn_save.clicked.connect(self._on_save_file)
            layout.addWidget(btn_save)

            btn_save_as = QPushButton("Save As...")
            btn_save_as.setIcon(_ICON_SAVE_AS_ICON)
            btn_save_as.clicked.connect(self._on_save_file_as)
            layout.addWidget(btn_save_as)

            layout.addWidget(self._create_separator())

            btn_backup = QPushButton("📦 Create Backup")
            btn_backup.clicked.connect(self._on_create_backup)
            layout.addWidget(btn_backup)

            btn_restore = QPushButton("📥 Restore Backup...")
            btn_restore.clicked.connect(self._on_restore_backup)
            layout.addWidget(btn_restore)

            return row

        def _create_filter_bar(self) -> QWidget:
            """Create the filter controls."""
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            layout.addWidget(QLabel("🔍 Filter:"))

            self._filter_input = QLineEdit()
            self._filter_input.setPlaceholderText(
                "Search command name or key..."
            )
            self._filter_input.textChanged.connect(self._on_filter_changed)
            layout.addWidget(self._filter_input, 1)

            layout.addWidget(QLabel("Room:"))

            self._room_combo = QComboBox()
            self._room_combo.setMinimumWidth(150)
            self._room_combo.currentTextChanged.connect(
                self._on_room_filter_changed)
            layout.addWidget(self._room_combo)

            self._issues_check = QCheckBox("Show Issues Only")
            self._issues_check.stateChanged.connect(self._on_filter_changed)
            layout.addWidget(self._issues_check)

            return row

        def _create_table(self) -> QTreeWidget:
            """Create the main data table."""
            table = QTreeWidget()
            table.setAlternatingRowColors(True)
            table.setRootIsDecorated(False)
            table.setSortingEnabled(True)
            table.setSelectionMode(QTreeWidget.ExtendedSelection)
            table.setContextMenuPolicy(Qt.CustomContextMenu)

            columns = ["Command", "Key", "Modifiers",
                       "Room", "Status", "UserDef", "Stack"]
            table.setHeaderLabels(columns)

            header = table.header()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(COL_COMMAND, QHeaderView.Stretch)
            header.setSectionResizeMode(COL_KEY, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(
                COL_MODIFIERS, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(COL_ROOM, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(
                COL_STATUS, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(
                COL_USER_DEF, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(
                COL_STACKABLE, QHeaderView.ResizeToContents)

            table.customContextMenuRequested.connect(
                self._on_table_context_menu)
            table.itemDoubleClicked.connect(self._on_cell_double_click)

            return table

        def _create_sidebar(self) -> QWidget:
            """Create the stats/info sidebar."""
            sidebar = QWidget()
            sidebar.setMaximumWidth(350)
            layout = QVBoxLayout(sidebar)
            layout.setContentsMargins(8, 0, 0, 0)
            layout.setSpacing(12)

            # Stats section
            stats_group = QGroupBox("📊 Statistics")
            stats_layout = QVBoxLayout(stats_group)
            self._stats_label = QLabel("Loading...")
            self._stats_label.setWordWrap(True)
            stats_layout.addWidget(self._stats_label)
            layout.addWidget(stats_group)

            # Issues summary
            issues_group = QGroupBox("⚠️ Issues")
            issues_layout = QVBoxLayout(issues_group)
            self._issues_label = QLabel("No issues")
            self._issues_label.setWordWrap(True)
            issues_layout.addWidget(self._issues_label)
            layout.addWidget(issues_group)

            # Garbage key config
            garbage_group = QGroupBox("🗑️ Garbage Key")
            garbage_layout = QVBoxLayout(garbage_group)

            self._garbage_label = QLabel(
                f"{self._garbage_key}\n"
                f"{'Ctrl+' if self._garbage_ctrl else ''}"
                f"{'Alt+' if self._garbage_alt else ''}"
                f"{'Shift+' if self._garbage_shift else ''}"
            )
            garbage_layout.addWidget(self._garbage_label)

            btn_config_garbage = QPushButton("⚙️ Configure...")
            btn_config_garbage.clicked.connect(self._on_configure_garbage_key)
            garbage_layout.addWidget(btn_config_garbage)

            garbage_info = QLabel(
                "<i>Some 3DCoat shortcuts can't be unmapped. "
                "Map them to a garbage key to disable.</i>"
            )
            garbage_info.setWordWrap(True)
            garbage_info.setStyleSheet("color: #888; font-size: 10px;")
            garbage_layout.addWidget(garbage_info)

            layout.addWidget(garbage_group)

            # Backups
            backup_group = QGroupBox("📦 Backups")
            backup_layout = QVBoxLayout(backup_group)
            self._backup_label = QLabel("0 backups available")
            backup_layout.addWidget(self._backup_label)
            layout.addWidget(backup_group)

            layout.addStretch()

            return sidebar

        def _create_separator(self) -> QFrame:
            """Create a vertical separator line."""
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet("color: #555;")
            return sep

        # =====================================================================
        # FILE OPERATIONS
        # =====================================================================

        def _load_file(self, path: Path) -> None:
            """Load a hotkeys file."""
            try:
                self._hotkeys_path = path
                self._hotkeys_file = parse_hotkeys_file(path)
                validate_all(self._hotkeys_file)

                self._file_label.setText(str(path))
                self._file_label.setStyleSheet("color: #90caf9;")

                self._update_room_filter()
                self._update_table()
                self._update_stats()
                self._update_backup_count()

                self._status_bar.showMessage(
                    f"Loaded {len(self._hotkeys_file.entries)} entries"
                )

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load file:\n{e}"
                )

        def _on_open_file(self) -> None:
            """Open file dialog to select a hotkeys file."""
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Hotkeys File",
                str(self._hotkeys_path.parent) if self._hotkeys_path else "",
                "XML Files (*.xml);;All Files (*)",
            )
            if path:
                self._load_file(Path(path))

        def _on_save_file(self) -> None:
            """Save the current file."""
            if not self._hotkeys_file or not self._hotkeys_path:
                return

            try:
                # Auto-backup before save
                create_backup(self._hotkeys_path)
                save_hotkeys_file(self._hotkeys_file, self._hotkeys_path)
                self._update_backup_count()
                self._status_bar.showMessage("File saved (backup created)")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to save:\n{e}"
                )

        def _on_save_file_as(self) -> None:
            """Save to a new file."""
            if not self._hotkeys_file:
                return

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Hotkeys File",
                str(self._hotkeys_path) if self._hotkeys_path else "",
                "XML Files (*.xml);;All Files (*)",
            )
            if path:
                try:
                    save_hotkeys_file(self._hotkeys_file, Path(path))
                    self._hotkeys_path = Path(path)
                    self._file_label.setText(str(path))
                    self._update_backup_count()
                    self._status_bar.showMessage(f"Saved to {path}")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to save:\n{e}"
                    )

        # =====================================================================
        # FILTER & TABLE UPDATE
        # =====================================================================

        def _update_room_filter(self) -> None:
            """Update room filter dropdown with rooms from file."""
            if not self._hotkeys_file:
                return

            current = self._room_combo.currentText()
            self._room_combo.blockSignals(True)
            self._room_combo.clear()

            self._room_combo.addItem("All")
            self._room_combo.addItem("(Global)")

            for room in sorted(self._hotkeys_file.get_unique_rooms()):
                if room:
                    self._room_combo.addItem(room)

            # Restore selection if possible
            idx = self._room_combo.findText(current)
            if idx >= 0:
                self._room_combo.setCurrentIndex(idx)

            self._room_combo.blockSignals(False)

        def _on_room_filter_changed(self, text: str) -> None:
            """Handle room filter change."""
            self._current_room_filter = text
            self._update_table()

        def _on_filter_changed(self) -> None:
            """Handle filter text or issues checkbox change."""
            self._current_filter_text = self._filter_input.text().strip().lower()
            self._show_only_issues = self._issues_check.isChecked()
            self._update_table()

        def _get_filtered_entries(self) -> list[HotkeyEntry]:
            """Get entries filtered by current criteria."""
            if not self._hotkeys_file:
                return []

            entries = self._hotkeys_file.entries

            # Room filter
            if self._current_room_filter == "(Global)":
                entries = [e for e in entries if e.room == ""]
            elif self._current_room_filter != "All":
                entries = [e for e in entries if e.room ==
                           self._current_room_filter]

            # Issues only filter
            if self._show_only_issues:
                entries = [e for e in entries if e.has_issues]

            # Text filter
            if self._current_filter_text:
                search = self._current_filter_text
                entries = [
                    e for e in entries
                    if search in e.id.lower()
                    or search in e.display_key.lower()
                    or search in e.room.lower()
                ]

            return entries

        def _update_table(self) -> None:
            """Update the table with filtered entries."""
            self._table.clear()

            entries = self._get_filtered_entries()
            for entry in entries:
                item = self._create_table_item(entry)
                self._table.addTopLevelItem(item)

            self._status_bar.showMessage(
                f"Showing {len(entries)} entries"
            )

        def _create_table_item(self, entry: HotkeyEntry) -> QTreeWidgetItem:
            """Create a table item for an entry."""
            item = QTreeWidgetItem()

            item.setText(COL_COMMAND, entry.id)
            item.setText(COL_KEY, entry.display_key)

            modifiers = []
            if entry.ctrl:
                modifiers.append("Ctrl")
            if entry.alt:
                modifiers.append("Alt")
            if entry.shift:
                modifiers.append("Shift")
            item.setText(COL_MODIFIERS, "+".join(modifiers)
                         if modifiers else "")

            item.setText(COL_ROOM, entry.room if entry.room else "(Global)")

            # Status column
            status = ""
            color = COLOR_NORMAL
            if entry.is_duplicate:
                status = ICON_DUPLICATE + " Dup"
                color = COLOR_DUPLICATE
            elif len(entry.conflict_ids) > 0:
                status = ICON_CONFLICT + " Conflict"
                color = COLOR_CONFLICT
            elif entry.is_orphan_room:
                status = ICON_ORPHAN + " Orphan"
                color = COLOR_ORPHAN
            elif self._is_garbage_key(entry):
                status = ICON_GARBAGE + " Garbage"
                color = COLOR_GARBAGE
            elif not entry.is_assigned:
                color = COLOR_UNASSIGNED

            item.setText(COL_STATUS, status)

            item.setText(COL_USER_DEF, str(entry.user_defined)
                         if entry.user_defined > 0 else "")
            item.setText(COL_STACKABLE, "✓" if entry.allow_stack else "")

            # Store entry reference
            item.setData(COL_COMMAND, Qt.UserRole, entry)

            # Set row color
            self._set_row_color(item, color)

            return item

        def _is_garbage_key(self, entry: HotkeyEntry) -> bool:
            """Check if entry uses the garbage key binding."""
            return (
                entry.code == self._garbage_key
                and entry.ctrl == self._garbage_ctrl
                and entry.alt == self._garbage_alt
                and entry.shift == self._garbage_shift
            )

        def _set_row_color(self, item: QTreeWidgetItem, color: str) -> None:
            """Set the foreground color for all columns in a row."""
            brush = QBrush(QColor(color))
            for col in range(item.columnCount()):
                item.setForeground(col, brush)

        # =====================================================================
        # STATS & INFO UPDATE
        # =====================================================================

        def _update_stats(self) -> None:
            """Update the statistics display."""
            if not self._hotkeys_file:
                self._stats_label.setText("No file loaded")
                return

            stats = get_stats(self._hotkeys_file)
            text = (
                f"<b>Total entries:</b> {stats.total_entries}<br>"
                f"<b>Assigned:</b> {stats.assigned_entries}<br>"
                f"<b>Unassigned:</b> {stats.unassigned_entries}<br>"
                f"<b>User-defined:</b> {stats.user_modified}<br>"
                f"<b>Unique rooms:</b> {stats.unique_rooms}<br>"
            )
            self._stats_label.setText(text)

            self._update_issues_summary()

        def _update_issues_summary(self) -> None:
            """Update the issues summary display."""
            if not self._hotkeys_file:
                self._issues_label.setText("No file loaded")
                return

            stats = get_stats(self._hotkeys_file)
            issues = []

            if stats.duplicates > 0:
                issues.append(f"⊗ {stats.duplicates} duplicates")
            if stats.conflicts > 0:
                issues.append(f"⚡ {stats.conflicts} conflicts")
            if stats.orphan_rooms > 0:
                issues.append(f"? {stats.orphan_rooms} orphan rooms")

            if issues:
                self._issues_label.setText("<br>".join(issues))
                self._issues_label.setStyleSheet("color: #ffb74d;")
            else:
                self._issues_label.setText("✅ No issues found")
                self._issues_label.setStyleSheet("color: #81c784;")

        def _update_backup_count(self) -> None:
            """Update the backup count display."""
            if not self._hotkeys_path:
                self._backup_label.setText("0 backups available")
                return

            backups = list_backups(self._hotkeys_path)
            count = len(backups)
            self._backup_label.setText(
                f"{count} backup{'s' if count != 1 else ''} available")

        # =====================================================================
        # CLEANUP ACTIONS
        # =====================================================================

        def _on_remove_duplicates(self) -> None:
            """Remove duplicate entries."""
            if not self._hotkeys_file:
                return

            unique_entries, count = remove_duplicates(
                self._hotkeys_file.entries)
            if count > 0:
                self._hotkeys_file.entries = unique_entries
                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage(
                    f"Removed {count} duplicates. Remember to save!"
                )
            else:
                self._status_bar.showMessage("No duplicates found")

        def _on_remove_orphans(self) -> None:
            """Remove entries with orphan rooms."""
            if not self._hotkeys_file:
                return

            filtered_entries, count = remove_orphan_rooms(
                self._hotkeys_file.entries)
            if count > 0:
                self._hotkeys_file.entries = filtered_entries
                validate_all(self._hotkeys_file)
                self._update_room_filter()
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage(
                    f"Removed {count} entries with orphan rooms. Remember to save!"
                )
            else:
                self._status_bar.showMessage("No orphan rooms found")

        def _on_remove_unassigned(self) -> None:
            """Remove unassigned entries."""
            if not self._hotkeys_file:
                return

            before = len(self._hotkeys_file.entries)
            self._hotkeys_file.entries = [
                e for e in self._hotkeys_file.entries if e.is_assigned
            ]
            count = before - len(self._hotkeys_file.entries)

            if count > 0:
                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage(
                    f"Removed {count} unassigned entries. Remember to save!"
                )
            else:
                self._status_bar.showMessage("No unassigned entries found")

        def _on_resolve_conflicts(self) -> None:
            """Open the conflict resolution dialog."""
            if not self._hotkeys_file:
                return

            # Check if there are any conflicts using the same logic as the dialog
            # This includes Global+Room conflicts, not just same-room conflicts
            conflict_count = count_conflicts(
                self._hotkeys_file,
                self._garbage_key,
                self._garbage_ctrl,
                self._garbage_alt,
                self._garbage_shift,
            )
            if conflict_count == 0:
                QMessageBox.information(
                    self, "No Conflicts", "No hotkey conflicts found."
                )
                return

            # Open dialog
            dialog = ConflictResolutionDialog(
                self._hotkeys_file,
                self,
                self._garbage_key,
                self._garbage_ctrl,
                self._garbage_alt,
                self._garbage_shift,
            )
            dialog.setStyleSheet(EDITOR_STYLESHEET)

            if dialog.exec() == QDialog.Accepted:
                # Re-validate and update
                validate_all(self._hotkeys_file)
                self._update_room_filter()
                self._update_table()
                self._update_stats()

                if dialog.has_changes():
                    self._status_bar.showMessage(
                        "Conflicts resolved. Remember to save!"
                    )
            elif dialog.has_changes():
                # User cancelled but made changes - they're already applied to entries
                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage("Changes applied (not saved)")

        # =====================================================================
        # BACKUP ACTIONS
        # =====================================================================

        def _on_create_backup(self) -> None:
            """Create a manual backup."""
            if not self._hotkeys_path:
                return

            try:
                backup_path = create_backup(self._hotkeys_path)
                self._update_backup_count()
                QMessageBox.information(
                    self,
                    "Backup Created",
                    f"Backup saved to:\n{backup_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to create backup: {e}"
                )

        def _on_configure_garbage_key(self) -> None:
            """Open dialog to configure the garbage key combination."""
            dialog = QDialog(self)
            dialog.setWindowTitle("Configure Garbage Key")
            dialog.setMinimumWidth(400)

            layout = QVBoxLayout(dialog)

            # Explanation
            info = QLabel(
                "<b>Garbage Key Combo</b><br><br>"
                "Some 3DCoat shortcuts cannot be unmapped - they respawn with defaults. "
                "Mapping them to an unused 'garbage key' combination is the only way to disable them.<br><br>"
                "Choose a key combo that you will never use for actual shortcuts."
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            # Key selection
            form = QFormLayout()

            key_input = QLineEdit(self._garbage_key)
            key_input.setPlaceholderText(
                "e.g., key_ScrollLock, key_Pause, key_NumLock")
            form.addRow("Key:", key_input)

            ctrl_check = QCheckBox("Ctrl")
            ctrl_check.setChecked(self._garbage_ctrl)

            alt_check = QCheckBox("Alt")
            alt_check.setChecked(self._garbage_alt)

            shift_check = QCheckBox("Shift")
            shift_check.setChecked(self._garbage_shift)

            mod_layout = QHBoxLayout()
            mod_layout.addWidget(ctrl_check)
            mod_layout.addWidget(alt_check)
            mod_layout.addWidget(shift_check)
            mod_layout.addStretch()

            form.addRow("Modifiers:", mod_layout)
            layout.addLayout(form)

            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() == QDialog.Accepted:
                # Update garbage key settings
                self._garbage_key = key_input.text().strip() or DEFAULT_GARBAGE_KEY
                self._garbage_ctrl = ctrl_check.isChecked()
                self._garbage_alt = alt_check.isChecked()
                self._garbage_shift = shift_check.isChecked()

                # Update label
                self._garbage_label.setText(
                    f"{self._garbage_key}\n"
                    f"{'Ctrl+' if self._garbage_ctrl else ''}"
                    f"{'Alt+' if self._garbage_alt else ''}"
                    f"{'Shift+' if self._garbage_shift else ''}"
                )

                # Re-validate table (garbage key status may have changed)
                self._update_table()
                self._status_bar.showMessage(
                    "Garbage key configuration updated")

        def _on_restore_backup(self) -> None:
            """Restore from a backup."""
            if not self._hotkeys_path:
                return

            backups = list_backups(self._hotkeys_path)
            if not backups:
                QMessageBox.information(
                    self, "No Backups", "No backups available."
                )
                return

            # Simple selection dialog - show most recent 10
            items = [
                f"{b.name} ({b.stat().st_size // 1024} KB)" for b in backups[:10]
            ]

            from PySide6.QtWidgets import QInputDialog
            item, ok = QInputDialog.getItem(
                self,
                "Restore Backup",
                "Select backup to restore:",
                items,
                0,
                False,
            )

            if ok and item:
                idx = items.index(item)
                backup_path = backups[idx]

                reply = QMessageBox.question(
                    self,
                    "Confirm Restore",
                    f"Restore from {backup_path.name}?\n\n"
                    "Current file will be backed up first.",
                    QMessageBox.Yes | QMessageBox.No,
                )

                if reply == QMessageBox.Yes:
                    try:
                        restore_backup(backup_path, self._hotkeys_path)
                        self._load_file(self._hotkeys_path)
                        self._status_bar.showMessage(
                            f"Restored from {backup_path.name}")
                    except Exception as e:
                        QMessageBox.critical(
                            self, "Error", f"Failed to restore: {e}"
                        )

        # =====================================================================
        # CONTEXT MENU & SELECTION
        # =====================================================================

        def _on_table_context_menu(self, pos) -> None:
            """Show context menu for table items."""
            selected_items = self._table.selectedItems()
            if not selected_items:
                return

            menu = QMenu(self)

            # Get selected entries
            selected_entries = [
                item.data(COL_COMMAND, Qt.UserRole)
                for item in selected_items
                if item.data(COL_COMMAND, Qt.UserRole) is not None
            ]

            count = len(selected_entries)

            # Edit actions
            if count == 1:
                entry = selected_entries[0]
                edit_menu = menu.addMenu("📝 Edit...")

                edit_key_action = edit_menu.addAction("🎹 Edit Key Binding...")
                edit_key_action.triggered.connect(
                    lambda: self._edit_key_binding([entry])
                )

                edit_room_action = edit_menu.addAction("🏠 Edit Room...")
                edit_room_action.triggered.connect(
                    lambda: self._edit_room([entry])
                )

                edit_cmd_action = edit_menu.addAction("📛 Edit Command ID...")
                edit_cmd_action.triggered.connect(
                    lambda: self._edit_command([entry])
                )

                unmap_action = edit_menu.addAction("🚫 Unmap Key")
                unmap_action.triggered.connect(self._bulk_unmap_keys)

                garbage_action = edit_menu.addAction("🗑️ Map to Garbage Key")
                garbage_action.triggered.connect(self._bulk_map_to_garbage)

            elif count > 1:
                edit_menu = menu.addMenu(f"📝 Edit {count} Selected...")

                edit_key_action = edit_menu.addAction("🎹 Set Key Binding...")
                edit_key_action.triggered.connect(
                    lambda: self._edit_key_binding(selected_entries)
                )

                room_menu = edit_menu.addMenu("🏠 Change Room")
                if self._hotkeys_file:
                    available_rooms = [""] + sorted(
                        r for r in self._hotkeys_file.get_unique_rooms() if r
                    )
                    for room in available_rooms:
                        display_name = "(Global)" if room == "" else room
                        action = room_menu.addAction(display_name)
                        action.setData(("room", room))
                        action.triggered.connect(
                            lambda checked, r=room: self._bulk_set_room(r)
                        )

                unmap_action = edit_menu.addAction("🚫 Unmap Keys")
                unmap_action.triggered.connect(self._bulk_unmap_keys)

                garbage_action = edit_menu.addAction("🗑️ Map to Garbage Key")
                garbage_action.triggered.connect(self._bulk_map_to_garbage)

            # View XML action (single entry only)
            if count == 1:
                menu.addSeparator()
                view_xml_action = menu.addAction("📄 View XML...")
                view_xml_action.triggered.connect(
                    lambda: self._view_entry_xml(selected_entries[0])
                )

            # Delete action
            menu.addSeparator()
            delete_action = menu.addAction(
                f"🗑️ Delete {count} Entr{'ies' if count > 1 else 'y'}"
            )
            delete_action.triggered.connect(self._delete_selected_entries)

            menu.exec_(self._table.mapToGlobal(pos))

        def _get_selected_entries(self) -> list[HotkeyEntry]:
            """Get HotkeyEntry objects for selected table items."""
            selected_items = self._table.selectedItems()
            return [
                item.data(COL_COMMAND, Qt.UserRole)
                for item in selected_items
                if item.data(COL_COMMAND, Qt.UserRole) is not None
            ]

        def _view_entry_xml(self, entry: HotkeyEntry) -> None:
            """Show the XML representation of an entry in a dialog."""
            xml_text = entry.to_xml()

            dialog = QDialog(self)
            dialog.setWindowTitle(f"XML: {entry.id}")
            dialog.setMinimumSize(500, 300)
            dialog.resize(600, 400)

            layout = QVBoxLayout(dialog)

            allow_stack_str = "✓" if entry.allow_stack else "✗"
            user_def_str = str(
                entry.user_defined) if entry.user_defined > 0 else "0 (default)"

            info = QLabel(
                f"<b>Command:</b> {entry.id}<br>"
                f"<b>Room:</b> {entry.room or '(Global)'}<br>"
                f"<b>Binding:</b> {entry.display_key}<br>"
                f"<b>AllowStack:</b> {allow_stack_str}<br>"
                f"<b>UserDefined:</b> {user_def_str}"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            from PySide6.QtWidgets import QTextEdit
            text_edit = QTextEdit()
            text_edit.setPlainText(xml_text)
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet(
                "font-family: 'Consolas', 'Courier New', monospace; "
                "font-size: 11px; background-color: #1e1e1e;"
            )
            layout.addWidget(text_edit, 1)

            button_layout = QHBoxLayout()
            copy_btn = QPushButton("📋 Copy to Clipboard")
            copy_btn.clicked.connect(lambda: self._copy_to_clipboard(xml_text))
            button_layout.addWidget(copy_btn)
            button_layout.addStretch()

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            dialog.exec()

        def _copy_to_clipboard(self, text: str) -> None:
            """Copy text to clipboard."""
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self._status_bar.showMessage("Copied to clipboard", 2000)

        # =====================================================================
        # BULK EDIT ACTIONS
        # =====================================================================

        def _bulk_set_room(self, room: str) -> None:
            """Set the room for all selected entries."""
            entries = self._get_selected_entries()
            if not entries:
                return

            for entry in entries:
                entry.room = room

            validate_all(self._hotkeys_file)
            self._update_room_filter()
            self._update_table()
            self._update_stats()

            display_room = "(Global)" if room == "" else room
            self._status_bar.showMessage(
                f"Changed room to '{display_room}' for {len(entries)} entries"
            )

        def _bulk_unmap_keys(self) -> None:
            """Unmap (set to unassigned) all selected entries."""
            entries = self._get_selected_entries()
            if not entries:
                return

            for entry in entries:
                entry.code = "key_00"
                entry.ctrl = False
                entry.alt = False
                entry.shift = False

            validate_all(self._hotkeys_file)
            self._update_table()
            self._update_stats()

            self._status_bar.showMessage(f"Unmapped {len(entries)} entries")

        def _bulk_map_to_garbage(self) -> None:
            """Map all selected entries to the garbage key combination."""
            entries = self._get_selected_entries()
            if not entries:
                return

            for entry in entries:
                entry.code = self._garbage_key
                entry.ctrl = self._garbage_ctrl
                entry.alt = self._garbage_alt
                entry.shift = self._garbage_shift

            validate_all(self._hotkeys_file)
            self._update_table()
            self._update_stats()

            self._status_bar.showMessage(
                f"Mapped {len(entries)} entr{'ies' if len(entries) > 1 else 'y'} to garbage key"
            )

        def _delete_selected_entries(self) -> None:
            """Delete the selected entries from the hotkeys file."""
            entries = self._get_selected_entries()
            if not entries or not self._hotkeys_file:
                return

            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Delete {len(entries)} hotkey entr{'ies' if len(entries) > 1 else 'y'}?\n\n"
                "This will permanently remove these entries from the file.\n"
                "Remember to save to apply changes.",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply != QMessageBox.Yes:
                return

            entries_to_delete = set(id(e) for e in entries)
            self._hotkeys_file.entries = [
                e for e in self._hotkeys_file.entries
                if id(e) not in entries_to_delete
            ]

            validate_all(self._hotkeys_file)
            self._update_room_filter()
            self._update_table()
            self._update_stats()

            self._status_bar.showMessage(f"Deleted {len(entries)} entries")

        # =====================================================================
        # CELL EDITING
        # =====================================================================

        def _on_cell_double_click(self, item: QTreeWidgetItem, column: int) -> None:
            """Handle double-click on a cell to edit it."""
            entry: HotkeyEntry | None = item.data(COL_COMMAND, Qt.UserRole)
            if not entry:
                return

            from PySide6.QtWidgets import QApplication
            modifiers = QApplication.keyboardModifiers()
            is_multi_edit = bool(modifiers & Qt.ShiftModifier)

            if is_multi_edit:
                entries = self._get_selected_entries()
                if not entries:
                    entries = [entry]
            else:
                entries = [entry]

            if column == COL_COMMAND:
                self._edit_command(entries)
            elif column == COL_KEY or column == COL_MODIFIERS:
                self._edit_key_binding(entries)
            elif column == COL_ROOM:
                self._edit_room(entries)
            elif column == COL_STACKABLE:
                self._edit_stackable(entries)

        def _edit_command(self, entries: list[HotkeyEntry]) -> None:
            """Edit the command ID for entries."""
            if not entries:
                return

            current = entries[0].id if len(entries) == 1 else ""

            from PySide6.QtWidgets import QInputDialog
            new_id, ok = QInputDialog.getText(
                self,
                "Edit Command",
                f"Command ID{f' (editing {len(entries)} entries)' if len(entries) > 1 else ''}:",
                QLineEdit.Normal,
                current,
            )

            if ok and new_id.strip():
                for entry in entries:
                    entry.id = new_id.strip()

                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage(
                    f"Updated command for {len(entries)} entr{'ies' if len(entries) > 1 else 'y'}"
                )

        def _edit_room(self, entries: list[HotkeyEntry]) -> None:
            """Edit the room for entries using a dropdown."""
            if not entries or not self._hotkeys_file:
                return

            available_rooms = sorted(self._hotkeys_file.get_unique_rooms())

            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Room")
            dialog.setMinimumWidth(300)

            layout = QVBoxLayout(dialog)

            label = QLabel(
                f"Select room{f' for {len(entries)} entries' if len(entries) > 1 else ''}:"
            )
            layout.addWidget(label)

            combo = QComboBox()
            combo.addItem("(Global)", "")
            for room in available_rooms:
                if room:
                    combo.addItem(room, room)

            if len(entries) == 1:
                current_room = entries[0].room
                for i in range(combo.count()):
                    if combo.itemData(i) == current_room:
                        combo.setCurrentIndex(i)
                        break

            layout.addWidget(combo)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() == QDialog.Accepted:
                new_room = combo.currentData()
                for entry in entries:
                    entry.room = new_room

                validate_all(self._hotkeys_file)
                self._update_room_filter()
                self._update_table()
                self._update_stats()

                display_room = "(Global)" if new_room == "" else new_room
                self._status_bar.showMessage(
                    f"Set room to '{display_room}' for {len(entries)} entr{'ies' if len(entries) > 1 else 'y'}"
                )

        def _edit_stackable(self, entries: list[HotkeyEntry]) -> None:
            """Toggle the stackable (allow_stack) flag for entries."""
            if not entries:
                return

            current_state = entries[0].allow_stack if len(
                entries) == 1 else False

            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Stackable")
            layout = QVBoxLayout(dialog)

            info = QLabel(
                f"Editing {len(entries)} entr{'ies' if len(entries) > 1 else 'y'}.\n\n"
                "Stackable shortcuts can coexist with other shortcuts using the same key binding.\n"
                "Non-stackable shortcuts will conflict with others on the same key."
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            checkbox = QCheckBox("Allow Stacking")
            checkbox.setChecked(current_state)
            layout.addWidget(checkbox)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() == QDialog.Accepted:
                new_state = checkbox.isChecked()
                for entry in entries:
                    entry.allow_stack = new_state

                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()

                state_str = "stackable" if new_state else "non-stackable"
                self._status_bar.showMessage(
                    f"Set {len(entries)} entr{'ies' if len(entries) > 1 else 'y'} to {state_str}"
                )

        def _edit_key_binding(self, entries: list[HotkeyEntry]) -> None:
            """Edit the key binding for entries using a key capture dialog."""
            if not entries:
                return

            dialog = KeyCaptureDialog(self, entries)
            if dialog.exec() == QDialog.Accepted:
                key_code, ctrl, alt, shift = dialog.get_binding()

                for entry in entries:
                    entry.code = key_code
                    entry.ctrl = ctrl
                    entry.alt = alt
                    entry.shift = shift

                validate_all(self._hotkeys_file)
                self._update_table()
                self._update_stats()
                self._status_bar.showMessage(
                    f"Updated binding for {len(entries)} entr{'ies' if len(entries) > 1 else 'y'}"
                )

else:
    # No Qt - provide dummy class for type hints
    class HotkeyEditorWindow:
        """Placeholder when Qt is not available."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("PySide6 is required for HotkeyEditorWindow")
