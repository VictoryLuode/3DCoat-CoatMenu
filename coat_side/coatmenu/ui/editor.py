"""
CoatMenu - the configuration editor.

A frameless, draggable panel (not a system window: no title bar, no taskbar
entry) that edits the same JSON the overlay reads:

* top row   - which list you are editing, plus new/rename/delete/reorder
* left      - the list's rows as a tree: drag to reorder, double-click to rename,
              submenus nest
* right     - the source catalog: 3DCoat commands, CustomMenu entries, scripts
* footer    - add submenu/header/separator, import/export, save & apply

Saving goes through ``core.menus.save_config``, which rewrites the launcher
scripts, the menu XML and (in a running 3DCoat) the menu items themselves.
"""
from __future__ import annotations

import json
import os
import re

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from coatmenu.core import bindings as bindings_mod
from coatmenu.core import catalog, menus, presets
from coatmenu.core.config import MenuConfig, Menu, item_to_json, preset_family
from coatmenu.core.log import log
from coatmenu.core.menu_model import (
    COMMAND,
    EXPAND_AUTO,
    EXPAND_LABELS,
    EXPAND_MODES,
    HEADER,
    PIE,
    PRESET,
    SCRIPT,
    SEPARATOR,
    SUBMENU,
    POSITION_AUTO,
    POSITION_LABELS,
    POSITION_MODES,
    MenuItem,
    flatten,
)
from coatmenu.ui import cursor as cursor_tool
from coatmenu.ui import system
from coatmenu.ui import theme

ROLE_KIND = Qt.UserRole + 1
ROLE_CID = Qt.UserRole + 2
ROLE_CMDS = Qt.UserRole + 3
ROLE_EXPAND = Qt.UserRole + 5
ROLE_POSITION = Qt.UserRole + 6

_TITLE_ROW_HEIGHT = 30
# Submenu labels we generate carry a row count ("Shade  (3)"); it belongs in the
# menu, not in a list name.
_COUNT_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")


def _menu_name_from(label: str) -> str:
    """The menu name a promoted submenu should get: its label, minus the count."""
    name = _COUNT_SUFFIX.sub("", (label or "").strip()).strip()
    return name or "Menu"

# The editor is mostly tree + catalog list, so it wants room: twice the original
# panel, capped to whatever screen it lands on (3DCoat is usually full-screen).
EDITOR_SIZE = QSize(1240, 840)


def _fit_to_screen(wanted: QSize) -> QSize:
    """*wanted* shrunk to fit the available screen area, if it does not."""
    try:
        area = QGuiApplication.primaryScreen().availableGeometry()
        return QSize(min(wanted.width(), int(area.width() * 0.95)),
                     min(wanted.height(), int(area.height() * 0.95)))
    except Exception:
        return wanted


def _css() -> str:
    """Dark styling that matches the overlay (3DCoat's chrome is dark too)."""
    # The panel's own background and border are painted in paintEvent: a plain
    # QWidget never draws a stylesheet background, which is why the panel used to
    # look transparent outside the child widgets.
    return f"""
    QLabel {{ color: rgb(224, 224, 224); font-size: 9pt; }}
    QLabel#coatmenuTitle {{ color: rgb(144, 202, 249); font-weight: bold; }}
    QLabel#coatmenuHint {{ color: rgb(136, 136, 136); }}
    QPushButton {{
        color: rgb(228, 228, 228); background: rgba(64, 66, 70, 255);
        border: 1px solid rgba(96, 98, 104, 255); border-radius: 4px;
        padding: 3px 8px; font-size: 9pt;
    }}
    QPushButton:hover {{ background: rgba(80, 84, 92, 255); }}
    QPushButton:pressed {{ background: rgba(58, 106, 160, 255); }}
    QPushButton#coatmenuPrimary {{
        background: rgba(58, 106, 160, 255); border-color: rgba(96, 150, 200, 255);
        font-weight: bold;
    }}
    QPushButton#coatmenuPrimary:hover {{ background: rgba(70, 122, 180, 255); }}
    QPushButton#coatmenuClose {{ padding: 1px 7px; }}
    QLineEdit, QComboBox {{
        color: rgb(228, 228, 228); background: rgba(32, 32, 34, 255);
        border: 1px solid rgba(96, 98, 104, 255); border-radius: 4px; padding: 2px 5px;
        font-size: 9pt;
    }}
    QTreeWidget, QListWidget {{
        color: rgb(228, 228, 228); background: rgba(32, 32, 34, 255);
        border: 1px solid rgba(85, 85, 85, 255); border-radius: 4px;
        font-size: 9pt; outline: none;
    }}
    QTreeWidget::item:selected, QListWidget::item:selected {{
        background: rgba(58, 106, 160, 255); color: white;
    }}
    QHeaderView::section {{
        color: rgb(200, 200, 200); background: rgba(52, 52, 54, 255);
        border: none; padding: 2px 5px; font-size: 9pt;
    }}
    """


class _CursorLayer(QWidget):
    """Transparent, click-through child that draws the pointer.

    The arrow cannot live in the panel's own paintEvent: Qt paints child widgets
    *after* their parent, so the tree/list widgets would cover the arrow exactly
    when the user is pointing at a row.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._position: QPoint | None = None

    def set_position(self, position: QPoint | None) -> None:
        if position == self._position:
            return
        self._position = position
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            cursor_tool.draw(painter, self._position)
        except Exception:
            log("editor cursor layer failed", exc=True)
        finally:
            painter.end()


class CoatMenuEditor(QWidget):
    """Frameless editor panel (one per process)."""

    MAX_UNDO = 30

    def __init__(self, config: MenuConfig | None = None) -> None:
        super().__init__(None)
        self._explicit_config = config is not None
        self._config = config or menus.get_config()
        self._index = 0
        self._sources_loaded = False
        self._drag_offset: QPoint | None = None
        self._dirty = False
        self._preview = None
        self._title_label: QLabel | None = None
        self._undo: list[str] = []
        self._redo: list[str] = []
        self._push_state()  # the starting point Ctrl+Z comes back to

        self.setObjectName("coatmenuEditor")
        self.setWindowTitle("CoatMenu")
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet(_css())
        self.resize(_fit_to_screen(EDITOR_SIZE))

        # The drawn pointer has to follow the real one even while it sits still
        # (3DCoat shows nothing at all in brush mode) - so poll for it rather than
        # relying on mouse-move events, which the child widgets swallow anyway.
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(theme.CURSOR_POLL_MS)
        self._cursor_timer.timeout.connect(self._sync_cursor)

        self._build()

        # Above every child widget, click-through, so the arrow is never covered.
        self._cursor_layer = _CursorLayer(self)
        self._cursor_layer.setGeometry(self.rect())
        self._cursor_layer.raise_()

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_title_row())
        root.addLayout(self._build_list_row())

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._build_items_panel(), 3)
        body.addWidget(self._build_sources_panel(), 2)
        root.addLayout(body, 1)

        root.addLayout(self._build_footer())

    def _mark_dirty(self) -> None:
        """Flag un-saved edits, show it in the title strip, and bank an undo point.

        Every edit already calls this, which is why the undo history is hung here
        instead of at a dozen call sites: one place to keep right.
        """
        self._dirty = True
        self.collect()
        self._push_state()
        self._refresh_title()

    def _refresh_title(self) -> None:
        label = getattr(self, "_title_label", None)
        if label is not None:
            label.setText("CoatMenu \u2014 Editor" + ("  *" if self._dirty else ""))

    def _build_title_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        title = QLabel("CoatMenu \u2014 Editor")
        title.setObjectName("coatmenuTitle")
        self._title_label = title
        row.addWidget(title)
        row.addStretch(1)
        self._status = QLabel("")
        self._status.setObjectName("coatmenuHint")
        row.addWidget(self._status)
        close = QPushButton("X")
        close.setObjectName("coatmenuClose")
        close.setFixedHeight(_TITLE_ROW_HEIGHT - 10)
        close.clicked.connect(self.close_editor)
        row.addWidget(close)
        return row

    def _build_list_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(QLabel("Menu"))
        self._menu_combo = QComboBox()
        self._menu_combo.setMinimumWidth(150)
        self._menu_combo.currentIndexChanged.connect(self.select_menu)
        row.addWidget(self._menu_combo)

        self._new_name = QLineEdit()
        self._new_name.setPlaceholderText("new menu name")
        self._new_name.setMaximumWidth(140)
        self._new_name.returnPressed.connect(self.add_menu)
        row.addWidget(self._new_name)

        # One button for "make a new menu": a blank one, or a shipped list back.
        # Two entry points side by side would just be more buttons on this row.
        self._new_button = QPushButton("+ New")
        self._new_menu = QMenu(self._new_button)
        self._new_button.setMenu(self._new_menu)
        self._new_button.setToolTip("A new empty menu, or a built-in list back")
        row.addWidget(self._new_button)

        for label, slot in (
            ("Rename", self.rename_menu),
            ("Delete", self.remove_menu),
            ("\u25b2", lambda: self.move_menu(-1)),
            ("\u25bc", lambda: self.move_menu(1)),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["List", "Pie"])
        self._mode_combo.setToolTip("How this menu opens: rows (List), or a radial Pie")
        self._mode_combo.currentIndexChanged.connect(self.set_mode_from_combo)
        row.addWidget(QLabel("Mode"))
        row.addWidget(self._mode_combo)

        row.addStretch(1)
        return row

    def _sync_mode_combo(self) -> None:
        target = self.current_menu
        index = 1 if (target is not None and target.mode == "pie") else 0
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentIndex(index)
        self._mode_combo.blockSignals(False)

    def set_mode_from_combo(self, index: int) -> None:
        """Persist the layout choice for the selected menu."""
        target = self.current_menu
        if target is None or index < 0:
            return
        mode = "pie" if index == 1 else "list"
        if mode == target.mode:
            return
        self._config.set_mode(target.name, mode)
        self.save()
        self._refresh_columns()   # the Where column only applies to a pie
        self.set_status(f"'{target.name}' opens as a {mode}")

    def _build_items_panel(self) -> QWidget:
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        hint = QLabel("Rows \u2014 drag to reorder, double-click to rename")
        hint.setToolTip("Expand: how a group unfolds (Auto / Inline / Panel).\n"
                        "Position: which way a row sits in a pie menu.")
        box.addWidget(hint)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Row", "Expand", "Position"])
        self._tree.setHeaderHidden(False)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setDragDropMode(QAbstractItemView.InternalMove)
        self._tree.setDefaultDropAction(Qt.MoveAction)
        self._tree.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self._tree.setIndentation(14)
        # Row takes whatever is left, the two control columns keep a fixed width -
        # otherwise the tree ends mid-panel with a band of dead space to its right.
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self._tree.setColumnWidth(1, 78)
        self._tree.setColumnWidth(2, 92)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_row_menu)
        self._tree.model().rowsMoved.connect(self._after_drop)
        box.addWidget(self._tree, 1)
        return panel

    def _after_drop(self, *_args) -> None:
        """A dropped row can become a group - give it its Expand control."""
        QTimer.singleShot(0, self._refresh_columns)

    def _build_sources_panel(self) -> QWidget:
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(QLabel("Add from"))

        self._source_kind = QComboBox()
        self._source_kind.addItems(
            ["3DCoat commands", "My tools", "Scripts"])
        self._source_kind.currentIndexChanged.connect(self.reload_sources)
        box.addWidget(self._source_kind)

        self._search = QLineEdit()
        self._search.setPlaceholderText("filter")
        self._search.textChanged.connect(self.reload_sources)
        box.addWidget(self._search)

        self._source_list = QListWidget()
        self._source_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._source_list.itemDoubleClicked.connect(lambda _i: self.add_source_item())
        # Entries are long and the panel is narrow: elide instead of offering a
        # horizontal scrollbar, and show the full text in a tooltip.
        self._source_list.setTextElideMode(Qt.ElideRight)
        self._source_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._source_list.setToolTip("double-click (or Add \u2192) to append to this menu; "
                                     "select several to add them in one go")
        box.addWidget(self._source_list, 1)

        add = QPushButton("Add \u2192")
        add.clicked.connect(self.add_source_item)
        box.addWidget(add)
        self._add_all = QPushButton("Add all")
        self._add_all.setToolTip("append everything the list is currently showing "
                                 "(filter first to narrow it down)")
        self._add_all.clicked.connect(self.add_all_sources)
        box.addWidget(self._add_all)
        return panel

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        for label, slot in (
            ("+ Submenu", self.add_submenu),
            ("+ Header", self.add_header),
            ("+ Separator", self.add_separator),
            ("Remove row", self.remove_row),
            ("Promote", self.promote_submenu),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        for label, slot in (
            ("Preview", self.preview_menu),
            ("Import", self.import_config),
            ("Export", self.export_config),
            ("Save & apply", self.save),
        ):
            button = QPushButton(label)
            if label.startswith("Save"):
                button.setObjectName("coatmenuPrimary")
            button.clicked.connect(slot)
            row.addWidget(button)
        return row

    # ------------------------------------------------------------------
    # painting
    # ------------------------------------------------------------------

    def paintEvent(self, _event) -> None:  # noqa: N802
        """Panel chrome.

        A plain QWidget draws neither a stylesheet background nor a border, and
        3DCoat may have hidden the system cursor (that part lives in
        ``_CursorLayer`` so child widgets cannot cover it).
        """
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)

            rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(QColor(*theme.BORDER), theme.BORDER_WIDTH))
            painter.setBrush(QColor(*theme.BG))
            painter.drawRoundedRect(rect, theme.CORNER_RADIUS, theme.CORNER_RADIUS)

            # a hairline under the title strip, so the panel reads as a window
            separator_y = 6 + _TITLE_ROW_HEIGHT
            painter.setPen(QPen(QColor(*theme.SEPARATOR), 1))
            painter.drawLine(int(theme.PADDING * 1.5), separator_y,
                             self.width() - int(theme.PADDING * 1.5), separator_y)
        except Exception:
            log("editor.paintEvent failed", exc=True)
        finally:
            painter.end()

    def _sync_cursor(self) -> None:
        """Keep the drawn pointer in step with the real one."""
        try:
            if not self.isVisible():
                return
            if not system.foreground_is_current_process():
                # 3DCoat is no longer in front - step aside instead of floating
                # over whatever the user switched to.
                self.close_editor()
                return
            self._cursor_layer.set_position(cursor_tool.local_position(self))
        except Exception:
            pass

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._cursor_layer.setGeometry(self.rect())
        self._cursor_layer.raise_()

    # ------------------------------------------------------------------
    # window behaviour
    # ------------------------------------------------------------------

    def show_editor(self) -> None:
        """Refresh from the config and show (idempotent)."""
        # An explicitly injected config (tests, previews) is authoritative; only
        # the singleton reads back from disk - and it keeps un-saved edits, so
        # stepping aside (switching applications) never throws work away.
        if not self._explicit_config and not self._dirty:
            self._config = menus.get_config()
        self.reload_menus()
        if self._dirty:
            self.set_status("un-saved edits kept - press Save & apply")
        self.center_on_screen()
        self.show()
        # Qt can adjust the frame size once the window is mapped; centring again in
        # the same event-loop turn keeps it exact without a visible jump.
        QTimer.singleShot(0, self.center_on_screen)
        self.raise_()
        self.setWindowOpacity(1.0)
        self._cursor_layer.setGeometry(self.rect())
        self._cursor_layer.raise_()
        self._cursor_timer.start()

    def center_on_screen(self) -> None:
        """Put the panel in the middle of the screen.

        The editor is opened from a menu entry, so there is no cursor position to
        anchor it to - and 3DCoat hides the pointer in brush mode anyway. The
        middle of the screen is the one place that is always easy to find.
        """
        try:
            area = QGuiApplication.primaryScreen().availableGeometry()
        except Exception:
            return
        x = int(area.left() + (area.width() - self.width()) / 2)
        y = int(area.top() + (area.height() - self.height()) / 2)
        # A panel bigger than the screen would land off the top-left corner.
        self.move(max(area.left(), x), max(area.top(), y))

    def _clamp_to_screen(self) -> None:
        """Keep the panel on screen - at 1240px it can hang off the right edge."""
        try:
            area = QGuiApplication.primaryScreen().availableGeometry()
        except Exception:
            return
        x = min(max(self.x(), area.left()), max(area.left(), area.right() - self.width()))
        y = min(max(self.y(), area.top()), max(area.top(), area.bottom() - self.height()))
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def close_editor(self) -> None:
        self._cursor_timer.stop()
        self._cursor_layer.set_position(None)
        self.close_preview()
        self.hide()

    # ------------------------------------------------------------------
    # live preview
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Delete removes the selected row, Escape closes the editor, Ctrl+Z undoes."""
        try:
            # getattr: the tests drive this with a minimal stand-in event.
            modifiers = getattr(event, "modifiers", lambda: Qt.NoModifier)()
            if modifiers & Qt.ControlModifier:
                if event.key() in (Qt.Key_Z, Qt.Key_Y):
                    if event.key() == Qt.Key_Y or modifiers & Qt.ShiftModifier:
                        self.redo()
                    else:
                        self.undo()
                    return
            if event.key() == Qt.Key_Delete:
                self.remove_row()
                return
            if event.key() == Qt.Key_Escape:
                self.close_editor()
                return
        except Exception:
            log("editor.keyPressEvent failed", exc=True)
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # undo / redo
    # ------------------------------------------------------------------

    def _push_state(self) -> None:
        """Remember the state *after* an edit.

        Hung off :meth:`_mark_dirty`, which every edit already calls, so there is
        no per-action bookkeeping to forget. Undo then means "drop the newest state
        and go back to the one before it".
        """
        try:
            state = json.dumps(self._config.to_json(), sort_keys=True)
        except Exception:
            return
        if self._undo and self._undo[-1] == state:
            return
        self._undo.append(state)
        del self._undo[:-self.MAX_UNDO]
        self._redo.clear()

    def _restore(self, state: str) -> None:
        self._config = MenuConfig.from_json(json.loads(state))
        self._index = min(self._index, max(0, len(self._config.menus) - 1))
        self.reload_menus()
        self._dirty = True
        self._refresh_title()

    def undo(self) -> None:
        """Step back one edit (Ctrl+Z)."""
        if len(self._undo) < 2:
            self.set_status("Nothing to undo")
            return
        try:
            self._redo.append(self._undo.pop())
            self._restore(self._undo[-1])
        except Exception as exc:
            self.set_status(f"Undo failed: {exc}")
            return
        self.set_status("Undid the last edit - Save & apply to keep it")

    def redo(self) -> None:
        """Step forward again (Ctrl+Shift+Z or Ctrl+Y)."""
        if not self._redo:
            self.set_status("Nothing to redo")
            return
        try:
            state = self._redo.pop()
            self._undo.append(state)
            self._restore(state)
        except Exception as exc:
            self.set_status(f"Redo failed: {exc}")
            return
        self.set_status("Redid the edit - Save & apply to keep it")

    def preview_menu(self) -> None:
        """Show the current rows exactly as the menu will open them.

        A separate overlay instance (not the singleton the hotkeys use), so a
        preview and a real menu never fight over one window. It uses the tree's
        *current* rows, so an un-saved edit can be looked at before committing.
        """
        target = self.current_menu
        if target is None:
            return
        from coatmenu.ui.popup import MenuPopup, title_item

        rows = self.tree_to_items()
        if not rows:
            self.set_status("nothing to preview yet")
            return
        mode = "pie" if target.mode == "pie" else "list"
        panel = self._preview
        if panel is None:
            panel = MenuPopup()
            self._preview = panel
        panel.set_mode(mode)
        panel.set_transient(False)
        panel.set_title(target.name)
        panel.set_items(rows if mode == "pie" else [title_item(target.name)] + rows)
        panel.show_at(self._preview_anchor())
        self.set_status(f"previewing '{target.name}' ({mode}) - it never runs anything")

    def _preview_anchor(self) -> QPoint:
        """Beside the editor when the screen has room, otherwise on its left.

        At 1240px wide the editor usually eats the right half of the screen, so
        the preview has to be able to fall back to the other side.
        """
        x = self.x() + self.width() + 18
        y = self.y() + 70
        try:
            area = QGuiApplication.primaryScreen().availableGeometry()
            if x + 260 > area.right():
                x = max(area.left(), self.x() - 260)
            y = min(y, max(area.top(), area.bottom() - 240))
        except Exception:
            pass
        return QPoint(int(x), int(y))

    def close_preview(self) -> None:
        panel = self._preview
        self._preview = None
        if panel is not None:
            panel.dismiss()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # drag the panel by its title strip
        if event.position().y() <= _TITLE_ROW_HEIGHT:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        else:
            self._drag_offset = None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802
        self._drag_offset = None

    # ------------------------------------------------------------------
    # list level
    # ------------------------------------------------------------------

    @property
    def current_menu(self) -> Menu | None:
        if 0 <= self._index < len(self._config.menus):
            return self._config.menus[self._index]
        return None

    def reload_menus(self) -> None:
        # Read the bindings first: the editor is where a missing key or two lists
        # fighting over one key should become visible.
        self._bindings = bindings_mod.describe(self._config)
        self._menu_combo.blockSignals(True)
        self._menu_combo.clear()
        for lst in self._config.menus:
            key = self._bindings.for_menu(lst.name)
            shape = "  pie" if lst.mode == PIE else ""
            self._menu_combo.addItem(
                f"{lst.name}  ({len(lst.items)})" + shape + (f"  [{key}]" if key else "")
            )
        self._index = min(self._index, max(0, len(self._config.menus) - 1))
        self._menu_combo.setCurrentIndex(self._index)
        self._menu_combo.blockSignals(False)
        self._menu_combo.setToolTip(self._bindings_tooltip())
        self.refresh_tree()
        self._sync_mode_combo()
        self._rebuild_new_menu()
        self.set_status("")
        if self._bindings.conflicts:
            self.set_status("Hotkey clash: " + "; ".join(self._bindings.conflicts))

    def _bindings_tooltip(self) -> str:
        """Keys per menu, plus any clashes - survives later status messages."""
        lines = [
            f"{lst.name}: {self._bindings.for_menu(lst.name) or 'unbound - bind it in Preferences > Hotkeys'}"
            for lst in self._config.menus
        ]
        if self._bindings.conflicts:
            lines.append("")
            lines.extend(self._bindings.conflicts)
        return "\n".join(lines)

    def select_menu(self, which) -> None:
        """Select a menu by index, or by name/slug."""
        if isinstance(which, str):
            target = self._config.find(which)
            which = self._config.menus.index(target) if target in self._config.menus else -1
        if which < 0:
            return
        self._index = which
        # Keep the dropdown in step: callers select by name as well as by click. The
        # combo may not know about this menu yet (it is rebuilt by reload_menus), so
        # refresh it first rather than setting an index it does not have.
        if which >= self._menu_combo.count():
            self.reload_menus()
        self._menu_combo.blockSignals(True)
        self._menu_combo.setCurrentIndex(which)
        self._menu_combo.blockSignals(False)
        self.refresh_tree()
        self._sync_mode_combo()

    def add_menu(self) -> None:
        name = self._new_name.text().strip()
        if not name:
            self.set_status("Type a name first")
            return
        lst = self._config.add_menu(name)
        self._new_name.clear()
        self._index = self._config.menus.index(lst)
        self.reload_menus()
        self._mark_dirty()
        self.set_status(f"Added menu '{lst.name}'")

    def preset_in_use(self, name: str) -> bool:
        """Whether a shipped list is already in the config (by name or by marker)."""
        if self._config.find(name) is not None:
            return True
        family = preset_family(presets.PRESET_MARKERS.get(name, ""))
        return any(preset_family(m.preset) == family for m in self._config.menus if m.preset)

    def add_builtin_menu(self, name: str) -> None:
        """Put one of the shipped lists back, built against the running 3D-Coat.

        The way back after Delete: deleting a built-in list is remembered so an
        install does not add it again, and this is what clears that memory.
        """
        if self.preset_in_use(name):
            self.set_status(f"'{name}' is already in your menus")
            return
        fresh = presets.build(name)
        if fresh is None:
            self.set_status(f"'{name}' is not a built-in list")
            return
        self._config.menus.append(fresh)
        # Both keys, so a list remembered by name comes back as readily as one
        # remembered by its preset family.
        for key in (preset_family(fresh.preset), preset_family(fresh.name)):
            self._config.forget_removed(key)
        self._index = self._config.menus.index(fresh)
        self.reload_menus()
        self._mark_dirty()
        self.set_status(f"Added built-in list '{fresh.name}' "
                        f"({len(fresh.items)} row(s)) \u2014 Save & apply to use it")

    def _rebuild_new_menu(self) -> None:
        """Refresh the '+ New' menu: a blank menu, then every shipped list."""
        menu = self._new_menu
        menu.clear()
        blank = menu.addAction("New empty menu")
        blank.triggered.connect(lambda _checked=False: self.add_menu())
        menu.addSeparator()
        heading = menu.addAction("Built-in lists")
        heading.setEnabled(False)
        for name in presets.BUILTIN_LISTS:
            in_use = self.preset_in_use(name)
            action = menu.addAction(f"    {name}" + ("    (in your menus)" if in_use else ""))
            action.setEnabled(not in_use)
            action.triggered.connect(
                lambda _checked=False, preset_name=name: self.add_builtin_menu(preset_name)
            )

    def rename_menu(self) -> None:
        target = self.current_menu
        if target is None:
            return
        new_name = self._new_name.text().strip()
        if not new_name:
            self.set_status("Type the new name in the field, then Rename")
            return
        # A menu's id (and so its hotkey id) is built from its name, and 3DCoat's
        # bindings are keyed by that id - so a rename leaves a key behind. We never
        # write 3DCoat's hotkey file, so say it instead of silently losing the key.
        bindings = getattr(self, "_bindings", None)
        old_key = bindings.for_menu(target.name) if bindings else ""
        self._config.rename_menu(target.name, new_name)
        self._new_name.clear()
        self.reload_menus()
        self._mark_dirty()
        note = ""
        if old_key:
            note = (f" - its id changed, so {old_key} no longer fires it "
                    f"(assign it again in 3D-Coat's Preferences > Hotkeys)")
        self.set_status(f"Renamed to '{self.current_menu.name}'{note}")

    def remove_menu(self) -> None:
        target = self.current_menu
        if target is None:
            return
        if not self._config.remove_menu(target.name):
            self.set_status("A config needs at least one menu")
            return
        self._index = max(0, self._index - 1)
        self.reload_menus()
        self._mark_dirty()
        self.set_status(f"Removed menu '{target.name}'")

    def move_menu(self, delta: int) -> None:
        target = self.current_menu
        if target is None:
            return
        if self._config.move_menu(target.name, delta):
            self._index = self._config.menus.index(target)
            self.reload_menus()
            self._mark_dirty()

    # ------------------------------------------------------------------
    # rows
    # ------------------------------------------------------------------

    def refresh_tree(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        target = self.current_menu
        if target is not None:
            for item in target.items:
                self._tree.addTopLevelItem(self._node_for(item))
        self._tree.expandAll()
        self._tree.blockSignals(False)
        self._refresh_columns()

    def _node_for(self, item: MenuItem) -> QTreeWidgetItem:
        node = QTreeWidgetItem([self._label_for(item)])
        node.setData(0, ROLE_KIND, item.kind)
        node.setData(0, ROLE_CID, item.cid or item.path)
        node.setData(0, ROLE_EXPAND, item.expand)
        node.setData(0, ROLE_POSITION, item.position)
        if item.cmds:
            node.setData(0, ROLE_CMDS, list(item.cmds))
            node.setToolTip(0, "runs in order: " + "  ->  ".join(item.cmds))
        elif item.path:
            node.setToolTip(0, item.path)
        elif item.cid:
            node.setToolTip(0, item.cid)
        flags = node.flags() | Qt.ItemIsEditable
        if item.kind == SUBMENU or item.children:
            flags |= Qt.ItemIsDropEnabled
        node.setFlags(flags)
        for child in item.children:
            node.addChild(self._node_for(child))
        return node

    # -- the Expand column ---------------------------------------------------

    def _is_group(self, node: QTreeWidgetItem) -> bool:
        """Rows that can unfold: a submenu, or anything holding children."""
        if (node.data(0, ROLE_KIND) or COMMAND) == SUBMENU:
            return True
        return node.childCount() > 0

    def _expand_combo(self, node: QTreeWidgetItem) -> QComboBox:
        """A fresh combo for one row, wired to write back into the node."""
        combo = QComboBox()
        for mode in EXPAND_MODES:
            combo.addItem(EXPAND_LABELS[mode], mode)
        current = node.data(0, ROLE_EXPAND) or EXPAND_AUTO
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.setToolTip(
            "Auto   - small groups open in the slot, big ones open a panel\n"
            "Inline - always open in the slot (pie) / always unfold\n"
            "Panel  - always open a separate panel")
        combo.currentIndexChanged.connect(
            lambda _i, n=node, c=combo: self._on_expand_changed(n, c))
        return combo

    def _on_expand_changed(self, node: QTreeWidgetItem, combo: QComboBox) -> None:
        mode = combo.currentData() or EXPAND_AUTO
        if node.data(0, ROLE_EXPAND) == mode:
            return
        node.setData(0, ROLE_EXPAND, mode)
        self._mark_dirty()
        self.set_status(f"'{node.text(0).strip()}' unfolds: {EXPAND_LABELS[mode]}")

    def _position_combo(self, node: QTreeWidgetItem) -> QComboBox:
        """Compass picker for a pie row."""
        combo = QComboBox()
        for spot in POSITION_MODES:
            combo.addItem(POSITION_LABELS[spot], spot)
        current = node.data(0, ROLE_POSITION) or POSITION_AUTO
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.setToolTip(
            "Where this row sits in a pie.\n"
            "Auto spreads the rows evenly, first one straight up.")
        combo.currentIndexChanged.connect(
            lambda _i, n=node, c=combo: self._on_position_changed(n, c))
        return combo

    def _on_position_changed(self, node: QTreeWidgetItem, combo: QComboBox) -> None:
        spot = combo.currentData() or POSITION_AUTO
        if node.data(0, ROLE_POSITION) == spot:
            return
        node.setData(0, ROLE_POSITION, spot)
        self._mark_dirty()
        self.set_status(f"'{node.text(0).strip()}' sits: {POSITION_LABELS[spot]}")

    def _refresh_columns(self) -> None:
        """Keep the Expand and Where controls in step with the tree.

        Called after a drop (a row can become a group) and after a rebuild, since
        the widgets do not survive ``clear()``. Where is only meaningful for a pie,
        so the column hides itself for a list.
        """
        menu = self.current_menu
        pie = bool(menu is not None and menu.mode == PIE)
        self._tree.setColumnHidden(2, not pie)

        self._tree.blockSignals(True)
        try:
            stack = [self._tree.topLevelItem(i)
                     for i in range(self._tree.topLevelItemCount())]
            while stack:
                node = stack.pop()
                if node is None:
                    continue
                stack.extend(node.child(i) for i in range(node.childCount()))
                if self._is_group(node):
                    if self._tree.itemWidget(node, 1) is None:
                        self._tree.setItemWidget(node, 1, self._expand_combo(node))
                else:
                    self._tree.removeItemWidget(node, 1)
                    node.setData(0, ROLE_EXPAND, EXPAND_AUTO)

                if pie and (node.data(0, ROLE_KIND) or COMMAND) not in (SEPARATOR, HEADER):
                    if self._tree.itemWidget(node, 2) is None:
                        self._tree.setItemWidget(node, 2, self._position_combo(node))
                else:
                    self._tree.removeItemWidget(node, 2)
                    node.setData(0, ROLE_POSITION, POSITION_AUTO)
        finally:
            self._tree.blockSignals(False)

    # kept for callers that only care about the Expand side
    def _refresh_expand_column(self) -> None:
        self._refresh_columns()

    @staticmethod
    def _label_for(item: MenuItem) -> str:
        if item.kind == SEPARATOR:
            return "------------"
        if item.kind == HEADER:
            return f"[{item.label}]"
        if item.kind == SUBMENU:
            return item.label
        return item.label or item.cid or item.path

    def _on_item_changed(self, node: QTreeWidgetItem, _column: int) -> None:
        """Mark dirty when a row is renamed in place."""
        kind = node.data(0, ROLE_KIND)
        text = node.text(0).strip()
        if kind == HEADER and text.startswith("[") and text.endswith("]"):
            node.setText(0, text[1:-1])
        self._mark_dirty()
        self.set_status("edited (remember to Save & apply)")

    def tree_to_items(self) -> list[MenuItem]:
        """Rebuild the data model from the tree (drag result included)."""
        return [self._item_from_node(self._tree.topLevelItem(i))
                for i in range(self._tree.topLevelItemCount())]

    def _item_from_node(self, node: QTreeWidgetItem) -> MenuItem:
        kind = node.data(0, ROLE_KIND) or COMMAND
        text = node.text(0).strip()
        cid = node.data(0, ROLE_CID) or ""
        expand = node.data(0, ROLE_EXPAND) or EXPAND_AUTO
        position = node.data(0, ROLE_POSITION) or POSITION_AUTO

        if kind == SEPARATOR:
            return MenuItem(kind=SEPARATOR)
        if kind == HEADER:
            label = text[1:-1] if text.startswith("[") and text.endswith("]") else text
            return MenuItem(label=label, kind=HEADER)

        # A row holding children is a group whatever its original kind: dragging a
        # command onto another one makes it a submenu, and its children must survive
        # the round trip.
        children = [self._item_from_node(node.child(i)) for i in range(node.childCount())]
        if children or kind == SUBMENU:
            return MenuItem(label=text, kind=SUBMENU, children=children,
                            expand=expand, position=position)

        if kind == SCRIPT:
            return MenuItem(label=text, kind=SCRIPT, path=cid, cid=cid)
        if kind == PRESET:
            return MenuItem(label=text, kind=PRESET, cid=cid)
        cmds = node.data(0, ROLE_CMDS) or []
        if cmds:
            return MenuItem(label=text, kind=COMMAND, cid=cid, cmds=list(cmds))
        return MenuItem(label=text, kind=COMMAND, cid=cid or text, position=position)

    def add_source_item(self) -> None:
        """Append the selected catalog rows (multi-select works)."""
        entries = self._source_list.selectedItems()
        if not entries:
            self.set_status("Pick something on the right")
            return
        added = sum(1 for entry in entries if self._append_source_entry(entry))
        if added:
            self._mark_dirty()
        self.set_status(f"Added {added} row(s)")

    def add_all_sources(self) -> None:
        """Append everything the source list is showing.

        Filter first to keep it to a group - this is how a whole 3DCoat menu
        section (22 Freeze commands, say) lands in one click instead of 22.
        """
        entries = [self._source_list.item(i) for i in range(self._source_list.count())]
        if not entries:
            self.set_status("Nothing to add")
            return
        added = sum(1 for entry in entries if self._append_source_entry(entry))
        if added:
            self._mark_dirty()
        self.set_status(f"Added all {added} row(s)")

    def _append_source_entry(self, entry) -> bool:
        """Turn one catalog row into a menu row (into the selected submenu, if any)."""
        cid = entry.data(Qt.UserRole) or ""
        if not cid:
            return False
        stored_kind = entry.data(Qt.UserRole + 2) or ""
        source = self._source_kind.currentIndex()
        # A stored kind wins: a source can mix commands and scripts, so the row
        # knows what it is better than the dropdown does.
        kind = stored_kind or (SCRIPT if source == 2 else COMMAND)
        label = entry.data(Qt.UserRole + 1) or (os.path.basename(cid) if kind == SCRIPT else cid)
        node = self._node_for(MenuItem(label=label, kind=kind, cid=cid,
                                       path=cid if kind == SCRIPT else ""))
        parent = self._tree.currentItem()
        if parent is not None and parent.data(0, ROLE_KIND) == SUBMENU:
            parent.addChild(node)
            parent.setExpanded(True)
        else:
            self._tree.addTopLevelItem(node)
        return True

    def add_submenu(self) -> None:
        node = self._node_for(MenuItem(label="New submenu", kind=SUBMENU))
        parent = self._tree.currentItem()
        if parent is not None and parent.data(0, ROLE_KIND) == SUBMENU:
            parent.addChild(node)
        else:
            self._tree.addTopLevelItem(node)
        self._tree.setCurrentItem(node)
        self._mark_dirty()
        self.set_status("Submenu added - double-click to rename")

    def _show_row_menu(self, pos: QPoint) -> None:
        """Right-click a row: move it elsewhere, or act on it."""
        node = self._tree.itemAt(pos)
        if node is None:
            return
        self._tree.setCurrentItem(node)
        self._row_menu().exec(self._tree.viewport().mapToGlobal(pos))

    def _row_menu(self) -> QMenu:
        """The row's context menu.

        Labels stay short: the right-click already says which row this is, so
        "Rename" beats "Rename this row".
        """
        node = self._tree.currentItem()
        item = self._item_from_node(node) if node is not None else MenuItem()
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: rgba(45, 46, 50, 255); color: rgb(228, 228, 228);"
            " border: 1px solid rgba(96, 98, 104, 255); padding: 2px; }"
            "QMenu::item { padding: 4px 18px; }"
            "QMenu::item:selected { background: rgba(58, 106, 160, 255); }"
            "QMenu::item:disabled { color: rgb(130, 130, 130); }")

        menu.addAction("Duplicate").triggered.connect(self.duplicate_row)

        copy_to = menu.addMenu("Copy to")
        move_to = menu.addMenu("Move to")
        targets = [lst for lst in self._config.menus if lst is not self.current_menu]
        if targets:
            for lst in targets:
                label = f"{lst.name}  ({len(lst.items)})"
                copy_to.addAction(label).triggered.connect(
                    lambda _checked=False, name=lst.name: self.copy_selected_to_list(name))
                move_to.addAction(label).triggered.connect(
                    lambda _checked=False, name=lst.name: self.move_selected_to_list(name))
        else:
            copy_to.setEnabled(False)
            move_to.setEnabled(False)

        menu.addSeparator()
        add = menu.addMenu("Add below")
        add.addAction("Submenu").triggered.connect(
            lambda: self.insert_row_after(SUBMENU))
        add.addAction("Header").triggered.connect(
            lambda: self.insert_row_after(HEADER))
        add.addAction("Separator").triggered.connect(
            lambda: self.insert_row_after(SEPARATOR))

        menu.addSeparator()
        promote = menu.addAction("Promote")
        promote.setEnabled(item.kind == SUBMENU and bool(item.children))
        promote.triggered.connect(self.promote_submenu)
        menu.addAction("Rename").triggered.connect(self.rename_row)
        menu.addAction("Delete").triggered.connect(self.remove_row)
        return menu

    def duplicate_row(self) -> None:
        """Copy the selected row (subtree included) right below itself."""
        node = self._tree.currentItem()
        if node is None:
            return
        copy_node = self._node_for(self._item_from_node(node))
        parent = node.parent() or self._tree.invisibleRootItem()
        parent.insertChild(parent.indexOfChild(node) + 1, copy_node)
        self._tree.setCurrentItem(copy_node)
        self._mark_dirty()
        self.set_status("Row duplicated")

    def copy_selected_to_list(self, target_name: str) -> None:
        """Copy the selected row (subtree included) into another menu."""
        node = self._tree.currentItem()
        target = self._config.find(target_name)
        if node is None or target is None or target is self.current_menu:
            return
        copied = self._item_from_node(node)
        self.collect()  # pick up anything edited in the tree before we add to it
        target.items.append(copied)
        self._mark_dirty()
        self.set_status(f"Copied '{copied.label or copied.cid}' to '{target.name}' "
                        f"({len(target.items)} rows)")

    def insert_row_after(self, kind: str) -> None:
        """Insert a submenu / header / separator right below the selected row."""
        new_item = MenuItem(label={SUBMENU: "New submenu", HEADER: "Section"}.get(kind, ""),
                            kind=kind)
        node = self._node_for(new_item)
        current = self._tree.currentItem()
        if current is None:
            self._tree.addTopLevelItem(node)
        else:
            parent = current.parent() or self._tree.invisibleRootItem()
            parent.insertChild(parent.indexOfChild(current) + 1, node)
        self._tree.setCurrentItem(node)
        self._mark_dirty()

    def move_selected_to_list(self, target_name: str) -> None:
        """Move the selected row (and anything under it) into another menu."""
        node = self._tree.currentItem()
        current = self.current_menu
        target = self._config.find(target_name)
        if node is None or current is None or target is None or target is current:
            return
        moved = self._item_from_node(node)

        # Same order as promoting: drop the row from the tree, collect, then hand
        # the row to its new list - so nothing edited in the tree is lost.
        parent = node.parent() or self._tree.invisibleRootItem()
        parent.removeChild(node)
        self.collect()
        target.items.append(moved)

        self.reload_menus()
        self.select_menu(target.name)
        self._mark_dirty()
        self.set_status(f"'{moved.label}' moved to '{target.name}'")

    def rename_row(self) -> None:
        """Start editing the selected row's label in place."""
        node = self._tree.currentItem()
        if node is not None:
            self._tree.editItem(node, 0)

    def promote_submenu(self) -> None:
        """Move the selected submenu out into a list of its own.

        A submenu and a top-level list hold the same thing - rows - so promoting
        one is a move, not a copy: its children become the new list, the row goes
        away, and the new list appears in the picker with its own
        ``CoatMenu_<Name>`` id to bind a hotkey to.
        """
        node = self._tree.currentItem()
        if node is None or node.data(0, ROLE_KIND) != SUBMENU:
            self.set_status("Select a submenu row to promote")
            return
        promoted = self._item_from_node(node)
        if not promoted.children:
            self.set_status(f"'{promoted.label}' has no rows - nothing to promote")
            return

        # Drop the row first, then collect: that leaves the config without it and
        # keeps anything edited in the tree on the way in.
        parent = node.parent() or self._tree.invisibleRootItem()
        parent.removeChild(node)
        self.collect()

        new_list = self._config.add_menu(_menu_name_from(promoted.label))
        new_list.items = promoted.children
        self.reload_menus()
        self.select_menu(new_list.name)
        self._mark_dirty()
        self.set_status(f"'{new_list.name}' is its own menu now - hover it in "
                        f"Scripts \u25b8 CoatMenu and press END to give it a key")

    def add_header(self) -> None:
        self._tree.addTopLevelItem(self._node_for(MenuItem(label="Section", kind=HEADER)))
        self._mark_dirty()

    def add_separator(self) -> None:
        self._tree.addTopLevelItem(self._node_for(MenuItem(kind=SEPARATOR)))
        self._mark_dirty()

    def remove_row(self) -> None:
        node = self._tree.currentItem()
        if node is None:
            self.set_status("Select a row first")
            return
        parent = node.parent()
        if parent is None:
            self._tree.takeTopLevelItem(self._tree.indexOfTopLevelItem(node))
        else:
            parent.removeChild(node)
        self._mark_dirty()

    # ------------------------------------------------------------------
    # sources
    # ------------------------------------------------------------------

    def reload_sources(self) -> None:
        if self._source_list is None:
            return
        needle = self._search.text().strip().lower()
        kind = self._source_kind.currentIndex()
        self._source_list.clear()
        rows: list[tuple[str, str, str, str]] = []  # text, cid, label, item kind

        if kind == 0:
            # The full command list: 3DCoat's own menus (~600) + hotkey ids +
            # custom-menu entries, with readable names where we have them.
            for entry in catalog.read_all_commands():
                where = entry.hint or entry.room or entry.source
                rows.append((f"{entry.label}  \u2014  {entry.cid}   [{where}]",
                             entry.cid, entry.label, COMMAND))
        elif kind == 1:
            # Your own tool presets (CustomTools/*.txt), resolved to the tool ids
            # 3DCoat's own panel uses - so a row added from here really does
            # switch the tool on the way out.
            for entry in catalog.read_my_tools():
                where = entry.hint or "tool"
                rows.append((f"{entry.label}  \u2014  {entry.cid}   [{where}]",
                             entry.cid, entry.label, COMMAND))
        elif kind == 2:
            for entry in catalog.read_script_commands():
                rows.append((entry.label, entry.cid, os.path.basename(entry.cid),
                             SCRIPT))

        shown = 0
        for text, cid, label, item_kind in rows:
            if needle and needle not in text.lower():
                continue
            node = QListWidgetItem(text)
            node.setData(Qt.UserRole, cid)
            node.setData(Qt.UserRole + 1, label)
            node.setData(Qt.UserRole + 2, item_kind)
            # The list is narrow and the entries are long; hovering shows the whole
            # thing rather than making you drag the horizontal scrollbar.
            node.setToolTip(text)
            self._source_list.addItem(node)
            shown += 1
            if shown >= 2000:
                break
        self._sources_loaded = True
        self._add_all.setText(f"Add all ({shown})")
        self._add_all.setEnabled(shown > 0)
        self.set_status(f"{shown} of {len(rows)} source(s)")

    # ------------------------------------------------------------------
    # load / save
    # ------------------------------------------------------------------

    def collect(self) -> MenuConfig:
        """Write the tree back into the config object."""
        target = self.current_menu
        if target is not None:
            target.items = self.tree_to_items()
        return self._config

    def save(self) -> None:
        try:
            config = self.collect()
            info = menus.save_config(config)
            self._config = config
            self._dirty = False
            self._refresh_title()
            self.reload_menus()
            if self._preview is not None:
                # Keep the preview honest: the rows may have just changed.
                self.preview_menu()
            self.set_status(
                f"Saved: {info['menus']} menu(s), {info['registered']} menu item(s) registered"
            )
            log(f"editor: saved ({info})")
        except Exception as exc:
            self.set_status(f"Save failed: {exc}")
            log("editor save failed", exc=True)

    def export_config(self) -> None:
        try:
            path, _filter = QFileDialog.getSaveFileName(self, "Export CoatMenu menus", "coatmenu-menus.json",
                                                        "JSON (*.json)")
            if not path:
                return
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self.collect().to_json(), fh, indent=2, ensure_ascii=False)
            self.set_status(f"Exported to {os.path.basename(path)}")
        except Exception as exc:
            self.set_status(f"Export failed: {exc}")

    def import_config(self) -> None:
        try:
            path, _filter = QFileDialog.getOpenFileName(self, "Import CoatMenu lists", "",
                                                        "JSON (*.json)")
            if not path:
                return
            with open(path, encoding="utf-8") as fh:
                imported = MenuConfig.from_json(json.load(fh))
            if not imported.menus:
                self.set_status("That file has no menus")
                return
            self._config = imported
            self._index = 0
            self.reload_menus()
            self.set_status("Imported - press Save & apply to keep it")
        except Exception as exc:
            self.set_status(f"Import failed: {exc}")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def set_status(self, text: str) -> None:
        try:
            self._status.setText(text)
        except Exception:
            pass

    def describe(self) -> list[dict]:
        """Debug helper: current menus as plain dicts."""
        return [{"name": lst.name, "rows": [item_to_json(i) for i in lst.items]}
                for lst in self.collect().menus]


_editor: CoatMenuEditor | None = None


def get_editor() -> CoatMenuEditor:
    global _editor
    if _editor is None:
        _editor = CoatMenuEditor()
    return _editor


def show_editor() -> None:
    get_editor().show_editor()
