"""
CoatMenu - the configuration editor.

A frameless, draggable panel (not a system window: no title bar, no taskbar
entry) that edits the same JSON the overlay reads:

* top row   - which list you are editing, plus new/rename/delete/reorder
* left      - the list's rows as a tree: drag to reorder, double-click to rename,
              submenus nest
* right     - the source catalog: 3DCoat commands, CustomMenu entries, scripts
* footer    - add submenu/header/separator, import/export, save & apply

Saving goes through ``core.lists.save_config``, which rewrites the launcher
scripts, the menu XML and (in a running 3DCoat) the menu items themselves.
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from coatmenu.core import bindings as bindings_mod
from coatmenu.core import catalog, lists
from coatmenu.core import lks as lks_mod
from coatmenu.core.config import MenuConfig, MenuList, item_to_json
from coatmenu.core.log import log
from coatmenu.core.menu_model import (
    COMMAND,
    HEADER,
    PRESET,
    SCRIPT,
    SEPARATOR,
    SUBMENU,
    MenuItem,
    flatten,
)
from coatmenu.ui import cursor as cursor_tool
from coatmenu.ui import system
from coatmenu.ui import theme

ROLE_KIND = Qt.UserRole + 1
ROLE_CID = Qt.UserRole + 2
ROLE_CMDS = Qt.UserRole + 3

_TITLE_ROW_HEIGHT = 30

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

    def __init__(self, config: MenuConfig | None = None) -> None:
        super().__init__(None)
        self._explicit_config = config is not None
        self._config = config or lists.get_config()
        self._index = 0
        self._sources_loaded = False
        self._drag_offset: QPoint | None = None
        self._dirty = False
        self._preview = None
        self._title_label: QLabel | None = None

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
        """Flag un-saved edits and show it in the title strip."""
        self._dirty = True
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
        row.addWidget(QLabel("List"))
        self._list_combo = QComboBox()
        self._list_combo.setMinimumWidth(150)
        self._list_combo.currentIndexChanged.connect(self.select_list)
        row.addWidget(self._list_combo)

        self._new_name = QLineEdit()
        self._new_name.setPlaceholderText("new list name")
        self._new_name.setMaximumWidth(140)
        self._new_name.returnPressed.connect(self.add_list)
        row.addWidget(self._new_name)

        for label, slot in (
            ("+ New", self.add_list),
            ("Rename", self.rename_list),
            ("Delete", self.remove_list),
            ("\u25b2", lambda: self.move_list(-1)),
            ("\u25bc", lambda: self.move_list(1)),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["List", "Pie"])
        self._mode_combo.setToolTip(
            "How this list opens: a vertical List, or a radial Pie menu"
        )
        self._mode_combo.currentIndexChanged.connect(self.set_mode_from_combo)
        row.addWidget(QLabel("as"))
        row.addWidget(self._mode_combo)
        row.addStretch(1)
        return row

    def _sync_mode_combo(self) -> None:
        target = self.current_list
        index = 1 if (target is not None and target.mode == "pie") else 0
        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentIndex(index)
        self._mode_combo.blockSignals(False)

    def set_mode_from_combo(self, index: int) -> None:
        """Persist the layout choice for the selected list."""
        target = self.current_list
        if target is None or index < 0:
            return
        mode = "pie" if index == 1 else "list"
        if mode == target.mode:
            return
        self._config.set_mode(target.name, mode)
        self.save()
        self.set_status(f"'{target.name}' opens as a {mode}")

    def _build_items_panel(self) -> QWidget:
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(QLabel("Rows (drag to reorder, double-click to rename)"))

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setDragDropMode(QAbstractItemView.InternalMove)
        self._tree.setDefaultDropAction(Qt.MoveAction)
        self._tree.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self._tree.setIndentation(14)
        self._tree.itemChanged.connect(self._on_item_changed)
        box.addWidget(self._tree, 1)
        return panel

    def _build_sources_panel(self) -> QWidget:
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(QLabel("Add from"))

        self._source_kind = QComboBox()
        self._source_kind.addItems(
            ["3DCoat commands", "My tools", "Presets", "LKS menus", "Scripts"])
        self._source_kind.currentIndexChanged.connect(self.reload_sources)
        box.addWidget(self._source_kind)

        self._search = QLineEdit()
        self._search.setPlaceholderText("filter")
        self._search.textChanged.connect(self.reload_sources)
        box.addWidget(self._search)

        self._source_list = QListWidget()
        self._source_list.itemDoubleClicked.connect(lambda _i: self.add_source_item())
        self._source_list.setToolTip("double-click (or Add \u2192) to append to the list")
        box.addWidget(self._source_list, 1)

        add = QPushButton("Add \u2192")
        add.clicked.connect(self.add_source_item)
        box.addWidget(add)
        return panel

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        for label, slot in (
            ("+ Submenu", self.add_submenu),
            ("+ Header", self.add_header),
            ("+ Separator", self.add_separator),
            ("Remove row", self.remove_row),
        ):
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        for label, slot in (
            ("Preview", self.preview_list),
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
            self._config = lists.get_config()
        self.reload_lists()
        if self._dirty:
            self.set_status("un-saved edits kept - press Save & apply")
        self._clamp_to_screen()
        self.show()
        self.raise_()
        self.setWindowOpacity(1.0)
        self._cursor_layer.setGeometry(self.rect())
        self._cursor_layer.raise_()
        self._cursor_timer.start()

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
        """Delete removes the selected row, Escape closes the editor."""
        try:
            if event.key() == Qt.Key_Delete:
                self.remove_row()
                return
            if event.key() == Qt.Key_Escape:
                self.close_editor()
                return
        except Exception:
            log("editor.keyPressEvent failed", exc=True)
        super().keyPressEvent(event)

    def preview_list(self) -> None:
        """Show the current rows exactly as the menu will open them.

        A separate overlay instance (not the singleton the hotkeys use), so a
        preview and a real menu never fight over one window. It uses the tree's
        *current* rows, so an un-saved edit can be looked at before committing.
        """
        target = self.current_list
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
    def current_list(self) -> MenuList | None:
        if 0 <= self._index < len(self._config.lists):
            return self._config.lists[self._index]
        return None

    def reload_lists(self) -> None:
        # Read the bindings first: the editor is where a missing key or two lists
        # fighting over one key should become visible.
        self._bindings = bindings_mod.describe(self._config)
        self._list_combo.blockSignals(True)
        self._list_combo.clear()
        for lst in self._config.lists:
            key = self._bindings.for_list(lst.name)
            self._list_combo.addItem(
                f"{lst.name}  ({len(lst.items)})" + (f"  [{key}]" if key else "")
            )
        self._index = min(self._index, max(0, len(self._config.lists) - 1))
        self._list_combo.setCurrentIndex(self._index)
        self._list_combo.blockSignals(False)
        self._list_combo.setToolTip(self._bindings_tooltip())
        self.refresh_tree()
        self._sync_mode_combo()
        self.set_status("")
        if self._bindings.conflicts:
            self.set_status("Hotkey clash: " + "; ".join(self._bindings.conflicts))

    def _bindings_tooltip(self) -> str:
        """Keys per list, plus any clashes - survives later status messages."""
        lines = [
            f"{lst.name}: {self._bindings.for_list(lst.name) or 'unbound - bind it in Preferences > Hotkeys'}"
            for lst in self._config.lists
        ]
        if self._bindings.conflicts:
            lines.append("")
            lines.extend(self._bindings.conflicts)
        return "\n".join(lines)

    def select_list(self, index: int) -> None:
        if index < 0:
            return
        self._index = index
        self.refresh_tree()
        self._sync_mode_combo()

    def add_list(self) -> None:
        name = self._new_name.text().strip()
        if not name:
            self.set_status("Type a name first")
            return
        lst = self._config.add_list(name)
        self._new_name.clear()
        self._index = self._config.lists.index(lst)
        self.reload_lists()
        self.set_status(f"Added list '{lst.name}'")

    def rename_list(self) -> None:
        target = self.current_list
        if target is None:
            return
        new_name = self._new_name.text().strip()
        if not new_name:
            self.set_status("Type the new name in the field, then Rename")
            return
        self._config.rename_list(target.name, new_name)
        self._new_name.clear()
        self.reload_lists()
        self.set_status(f"Renamed to '{self.current_list.name}'")

    def remove_list(self) -> None:
        target = self.current_list
        if target is None:
            return
        if not self._config.remove_list(target.name):
            self.set_status("A config needs at least one list")
            return
        self._index = max(0, self._index - 1)
        self.reload_lists()
        self.set_status(f"Removed list '{target.name}'")

    def move_list(self, delta: int) -> None:
        target = self.current_list
        if target is None:
            return
        if self._config.move_list(target.name, delta):
            self._index = self._config.lists.index(target)
            self.reload_lists()

    # ------------------------------------------------------------------
    # rows
    # ------------------------------------------------------------------

    def refresh_tree(self) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()
        target = self.current_list
        if target is not None:
            for item in target.items:
                self._tree.addTopLevelItem(self._node_for(item))
        self._tree.expandAll()
        self._tree.blockSignals(False)

    def _node_for(self, item: MenuItem) -> QTreeWidgetItem:
        node = QTreeWidgetItem([self._label_for(item)])
        node.setData(0, ROLE_KIND, item.kind)
        node.setData(0, ROLE_CID, item.cid or item.path)
        if item.cmds:
            node.setData(0, ROLE_CMDS, list(item.cmds))
            node.setToolTip(0, "runs in order: " + "  ->  ".join(item.cmds))
        flags = node.flags() | Qt.ItemIsEditable
        if item.kind == SUBMENU:
            flags |= Qt.ItemIsDropEnabled
        node.setFlags(flags)
        for child in item.children:
            node.addChild(self._node_for(child))
        return node

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

        if kind == SEPARATOR:
            return MenuItem(kind=SEPARATOR)
        if kind == HEADER:
            label = text[1:-1] if text.startswith("[") and text.endswith("]") else text
            return MenuItem(label=label, kind=HEADER)
        if kind == SUBMENU:
            children = [self._item_from_node(node.child(i)) for i in range(node.childCount())]
            return MenuItem(label=text, kind=SUBMENU, children=children)
        if kind == SCRIPT:
            return MenuItem(label=text, kind=SCRIPT, path=cid, cid=cid)
        if kind == PRESET:
            return MenuItem(label=text, kind=PRESET, cid=cid)
        cmds = node.data(0, ROLE_CMDS) or []
        if cmds:
            return MenuItem(label=text, kind=COMMAND, cid=cid, cmds=list(cmds))
        return MenuItem(label=text, kind=COMMAND, cid=cid or text)

    def add_source_item(self) -> None:
        entry = self._source_list.currentItem()
        if entry is None:
            self.set_status("Pick something from the list on the right")
            return
        cid = entry.data(Qt.UserRole) or ""
        stored_kind = entry.data(Qt.UserRole + 2) or ""
        source = self._source_kind.currentIndex()
        # A stored kind wins: the LKS source mixes commands and scripts, so the
        # row knows what it is better than the dropdown does.
        kind = stored_kind or (SCRIPT if source == 4 else
                               (PRESET if source == 2 else COMMAND))
        label = entry.data(Qt.UserRole + 1) or (os.path.basename(cid) if kind == SCRIPT else cid)
        new_item = MenuItem(label=label, kind=kind, cid=cid, path=cid if kind == SCRIPT else "")

        parent = self._tree.currentItem()
        node = self._node_for(new_item)
        if parent is not None and parent.data(0, ROLE_KIND) == SUBMENU:
            parent.addChild(node)
            parent.setExpanded(True)
        else:
            self._tree.addTopLevelItem(node)
        self._mark_dirty()
        self.set_status(f"Added {label}")

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
            # Your saved tool presets - a tool *plus* its settings.
            for entry in catalog.read_presets():
                rows.append((f"{entry.label}  \u2014  preset", entry.cid, entry.label,
                             PRESET))
        elif kind == 3:
            # The LKS extension's radial menus, flattened. LKS rows carry their
            # own kind, so a script stays a script when you add it.
            flat: list[MenuItem] = []
            for menu in lks_mod.read_menus():
                flat.extend(flatten(menu.items))
            for row in flat:
                if not row.clickable:
                    continue
                target = row.path or row.cid
                rows.append((f"{row.label}  \u2014  {target}   [LKS]", target,
                             row.label, row.kind))
        else:
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
            node.setToolTip(text)
            self._source_list.addItem(node)
            shown += 1
            if shown >= 2000:
                break
        self._sources_loaded = True
        self.set_status(f"{shown} of {len(rows)} source(s)")

    # ------------------------------------------------------------------
    # load / save
    # ------------------------------------------------------------------

    def collect(self) -> MenuConfig:
        """Write the tree back into the config object."""
        target = self.current_list
        if target is not None:
            target.items = self.tree_to_items()
        return self._config

    def save(self) -> None:
        try:
            config = self.collect()
            info = lists.save_config(config)
            self._config = config
            self._dirty = False
            self._refresh_title()
            self.reload_lists()
            if self._preview is not None:
                # Keep the preview honest: the rows may have just changed.
                self.preview_list()
            self.set_status(
                f"Saved: {info['lists']} list(s), {info['registered']} menu item(s) registered"
            )
            log(f"editor: saved ({info})")
        except Exception as exc:
            self.set_status(f"Save failed: {exc}")
            log("editor save failed", exc=True)

    def export_config(self) -> None:
        try:
            path, _filter = QFileDialog.getSaveFileName(self, "Export CoatMenu lists", "coatmenu-lists.json",
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
            if not imported.lists:
                self.set_status("That file has no lists")
                return
            self._config = imported
            self._index = 0
            self.reload_lists()
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
        """Debug helper: current lists as plain dicts."""
        return [{"name": lst.name, "rows": [item_to_json(i) for i in lst.items]}
                for lst in self.collect().lists]


_editor: CoatMenuEditor | None = None


def get_editor() -> CoatMenuEditor:
    global _editor
    if _editor is None:
        _editor = CoatMenuEditor()
    return _editor


def show_editor() -> None:
    get_editor().show_editor()
