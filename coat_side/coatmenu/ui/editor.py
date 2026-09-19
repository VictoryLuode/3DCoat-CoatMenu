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

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
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

from coatmenu.core import catalog, lists
from coatmenu.core.config import MenuConfig, MenuList, item_to_json
from coatmenu.core.log import log
from coatmenu.core.menu_model import COMMAND, HEADER, SCRIPT, SEPARATOR, SUBMENU, MenuItem
from coatmenu.ui import cursor as cursor_tool
from coatmenu.ui import system
from coatmenu.ui import theme

ROLE_KIND = Qt.UserRole + 1
ROLE_CID = Qt.UserRole + 2

_TITLE_ROW_HEIGHT = 30


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

        self.setObjectName("coatmenuEditor")
        self.setWindowTitle("CoatMenu")
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet(_css())
        self.resize(620, 420)

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

    def _build_title_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        title = QLabel("CoatMenu \u2014 Editor")
        title.setObjectName("coatmenuTitle")
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
        row.addStretch(1)
        return row

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
        self._source_kind.addItems(["3DCoat commands", "CustomMenu entries", "Scripts"])
        self._source_kind.currentIndexChanged.connect(self.reload_sources)
        box.addWidget(self._source_kind)

        self._search = QLineEdit()
        self._search.setPlaceholderText("filter")
        self._search.textChanged.connect(self.reload_sources)
        box.addWidget(self._search)

        self._source_list = QListWidget()
        self._source_list.itemDoubleClicked.connect(lambda _i: self.add_source_item())
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
            ("Import", self.import_config),
            ("Export", self.export_config),
            ("Save & apply", self.save),
        ):
            button = QPushButton(label)
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
        self.show()
        self.raise_()
        self.setWindowOpacity(1.0)
        self._cursor_layer.setGeometry(self.rect())
        self._cursor_layer.raise_()
        self._cursor_timer.start()

    def close_editor(self) -> None:
        self._cursor_timer.stop()
        self._cursor_layer.set_position(None)
        self.hide()

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
        self._list_combo.blockSignals(True)
        self._list_combo.clear()
        for lst in self._config.lists:
            self._list_combo.addItem(f"{lst.name}  ({len(lst.items)})")
        self._index = min(self._index, max(0, len(self._config.lists) - 1))
        self._list_combo.setCurrentIndex(self._index)
        self._list_combo.blockSignals(False)
        self.refresh_tree()
        self.set_status("")

    def select_list(self, index: int) -> None:
        if index < 0:
            return
        self._index = index
        self.refresh_tree()

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
        self._dirty = True
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
        return MenuItem(label=text, kind=COMMAND, cid=cid or text)

    def add_source_item(self) -> None:
        entry = self._source_list.currentItem()
        if entry is None:
            self.set_status("Pick something from the list on the right")
            return
        cid = entry.data(Qt.UserRole) or ""
        kind = SCRIPT if self._source_kind.currentIndex() == 2 else COMMAND
        label = entry.text().split("  \u2014  ")[0] if kind == COMMAND else (cid or entry.text())
        new_item = MenuItem(label=label, kind=kind, cid=cid, path=cid if kind == SCRIPT else "")

        parent = self._tree.currentItem()
        node = self._node_for(new_item)
        if parent is not None and parent.data(0, ROLE_KIND) == SUBMENU:
            parent.addChild(node)
            parent.setExpanded(True)
        else:
            self._tree.addTopLevelItem(node)
        self._dirty = True
        self.set_status(f"Added {label}")

    def add_submenu(self) -> None:
        node = self._node_for(MenuItem(label="New submenu", kind=SUBMENU))
        parent = self._tree.currentItem()
        if parent is not None and parent.data(0, ROLE_KIND) == SUBMENU:
            parent.addChild(node)
        else:
            self._tree.addTopLevelItem(node)
        self._tree.setCurrentItem(node)
        self._dirty = True
        self.set_status("Submenu added - double-click to rename")

    def add_header(self) -> None:
        self._tree.addTopLevelItem(self._node_for(MenuItem(label="Section", kind=HEADER)))
        self._dirty = True

    def add_separator(self) -> None:
        self._tree.addTopLevelItem(self._node_for(MenuItem(kind=SEPARATOR)))
        self._dirty = True

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
        self._dirty = True

    # ------------------------------------------------------------------
    # sources
    # ------------------------------------------------------------------

    def reload_sources(self) -> None:
        if self._source_list is None:
            return
        needle = self._search.text().strip().lower()
        kind = self._source_kind.currentIndex()
        self._source_list.clear()
        rows: list[tuple[str, str]] = []

        if kind == 0:
            for entry in catalog.read_hotkey_commands():
                rows.append((f"{entry.cid}  \u2014  {entry.room or 'global'}", entry.cid))
            for entry in catalog.read_custom_menu_commands():
                rows.append((f"{entry.label}  \u2014  {entry.cid}", entry.cid))
        elif kind == 1:
            for entry in catalog.read_custom_menu_commands():
                rows.append((f"{entry.label}  \u2014  {entry.cid}", f"${entry.cid}"))
        else:
            for entry in catalog.read_script_commands():
                rows.append((entry.label, entry.cid))

        for text, cid in rows:
            if needle and needle not in text.lower():
                continue
            node = QListWidgetItem(text)
            node.setData(Qt.UserRole, cid)
            self._source_list.addItem(node)
            if self._source_list.count() >= 400:
                break
        self._sources_loaded = True
        self.set_status(f"{self._source_list.count()} source(s) (of {len(rows)})")

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
            self.reload_lists()
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
