"""QGripBoxContainer — Vertical container with drag-drop reordering.

A container that wraps child widgets in grip boxes and allows reordering
via drag-drop. Each child gets a grip column on the left for dragging.

Supports live-preview reordering: items physically move during drag to
show where they will be placed on drop, alongside a visual drop indicator.
"""
from __future__ import annotations

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from ported.lks_utils.gui_qt.widgets.grip_box_item import QGripBoxItem


class QGripBoxContainer(QWidget):
    """Vertical container with drag-drop reordering support.

    Wraps child widgets in grip boxes and allows reordering via drag-drop.
    Each child gets a grip column on the left for dragging.

    Signals:
        order_changed: Emitted when items are reordered

    Args:
        parent: Parent widget

    Example:
        container = QGripBoxContainer()
        container.add_widget(my_widget, item_id="widget1")
        container.add_widget(my_button, item_id="button2")
        layout.addWidget(container)

        # Get current order
        order = container.get_order()  # ['widget1', 'button2']

        # Reorder programmatically
        container.set_order(['button2', 'widget1'])
    """

    order_changed = Signal(list)  # List of item IDs in new order

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize grip box container.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._items: list[QGripBoxItem] = []
        self._drag_item: QGripBoxItem | None = None
        self._drop_indicator: QFrame | None = None

        # Main layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(1)

        # Enable drop
        self.setAcceptDrops(True)

    def add_widget(
        self, widget: QWidget, item_id: str | None = None
    ) -> QGripBoxItem:
        """Add a widget to the container with a grip column.

        Args:
            widget: Widget to add
            item_id: Optional identifier for the item

        Returns:
            The QGripBoxItem wrapper
        """
        item = QGripBoxItem(widget, item_id, self)
        self._items.append(item)
        self._layout.addWidget(item)
        return item

    def remove_widget(self, widget: QWidget) -> bool:
        """Remove a widget from the container.

        Args:
            widget: Content widget to remove

        Returns:
            True if removed, False if not found
        """
        for item in self._items[:]:
            if item.content_widget == widget:
                self._items.remove(item)
                self._layout.removeWidget(item)
                item.deleteLater()
                self.order_changed.emit(self.get_order())
                return True
        return False

    def clear(self) -> None:
        """Remove all widgets from the container."""
        for item in self._items[:]:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def count(self) -> int:
        """Get number of items in container.

        Returns:
            Number of items
        """
        return len(self._items)

    def item_at(self, index: int) -> QGripBoxItem | None:
        """Get item at given index.

        Args:
            index: Index of item

        Returns:
            QGripBoxItem at index, or None if out of bounds
        """
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def insert_widget(
        self, index: int, widget: QWidget, item_id: str | None = None
    ) -> QGripBoxItem:
        """Insert a widget at a specific position in the container.

        Args:
            index: Position to insert at (0 = top of list).
            widget: Widget to add.
            item_id: Optional identifier for the item.

        Returns:
            The QGripBoxItem wrapper.
        """
        item = QGripBoxItem(widget, item_id, self)
        index = max(0, min(index, len(self._items)))
        self._items.insert(index, item)
        self._layout.insertWidget(index, item)
        return item

    def add_item(self, item: QGripBoxItem) -> None:
        """Add a pre-created QGripBoxItem to the container.

        Args:
            item: QGripBoxItem to add
        """
        self._items.append(item)
        self._layout.addWidget(item)

    def get_order(self) -> list[str]:
        """Get current order of items by their IDs.

        Returns:
            List of item IDs in current order
        """
        return [item.item_id for item in self._items if item.item_id is not None]

    def set_order(self, item_ids: list[str]) -> None:
        """Reorder items to match the given ID order.

        Args:
            item_ids: List of item IDs in desired order
        """
        # Create mapping of item_id -> item
        item_map = {
            item.item_id: item for item in self._items if item.item_id is not None
        }

        # Reorder items
        new_items: list[QGripBoxItem] = []
        for item_id in item_ids:
            if item_id in item_map:
                new_items.append(item_map[item_id])

        # Add any items not in the order list at the end
        for item in self._items:
            if item not in new_items:
                new_items.append(item)

        # Update internal list and layout
        self._items = new_items
        for i, item in enumerate(self._items):
            self._layout.removeWidget(item)
            self._layout.insertWidget(i, item)

    # -------------------------------------------------------------------------
    # Drag & Drop with Live Preview Reorder
    # -------------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag events and identify the dragged item."""
        if event.mimeData().hasText():
            mime_text = event.mimeData().text()
            for item in self._items:
                if mime_text == f"grip_box_{id(item)}":
                    self._drag_item = item
                    break
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Live-preview reorder + drop indicator during drag.

        Items physically move in real time to show where the dragged
        item will be placed, while a drop indicator provides an
        additional visual cue at the insertion point.
        """
        if not event.mimeData().hasText() or not self._drag_item:
            return

        # Find insertion index based on cursor position
        insert_idx = self._get_insert_index(event.position().toPoint())

        # Get current position of the dragged item
        current_idx = self._items.index(self._drag_item)

        # Live preview: physically move the item to the new position
        if current_idx != insert_idx:
            # Remove from old position
            self._items.remove(self._drag_item)
            self._layout.removeWidget(self._drag_item)

            # Adjust insert index if we removed before it
            if current_idx < insert_idx:
                insert_idx -= 1

            # Insert at new position
            self._items.insert(insert_idx, self._drag_item)
            self._layout.insertWidget(insert_idx, self._drag_item)

        # Update drop indicator as an additional visual cue
        self._update_drop_indicator(insert_idx)

        event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Hide drop indicator and clear drag state on leave."""
        if self._drop_indicator:
            self._drop_indicator.hide()
        self._drag_item = None

    def dropEvent(self, event: QDropEvent) -> None:
        """Finalize drop — reordering already happened in dragMoveEvent."""
        if self._drop_indicator:
            self._drop_indicator.hide()

        if not self._drag_item:
            return

        # Emit order_changed since the reorder happened during dragMoveEvent
        self.order_changed.emit(self.get_order())

        self._drag_item = None
        event.acceptProposedAction()

    def _get_insert_index(self, pos: QPoint) -> int:
        """Calculate insertion index based on cursor position.

        Args:
            pos: Cursor position in container coordinates

        Returns:
            Index where item should be inserted
        """
        for i, item in enumerate(self._items):
            item_center = item.pos().y() + item.height() // 2
            if pos.y() < item_center:
                return i
        return len(self._items)

    def _update_drop_indicator(self, insert_idx: int) -> None:
        """Create or update the drop indicator line at the insertion point.

        Args:
            insert_idx: Index where the item would be inserted
        """
        if not self._drop_indicator:
            self._drop_indicator = QFrame(self)
            self._drop_indicator.setFixedHeight(2)
            self._drop_indicator.setStyleSheet(
                "background-color: #90caf9; border-radius: 1px;"
            )

        # Position indicator at the insertion point
        if insert_idx < len(self._items):
            target_item = self._items[insert_idx]
            target_pos = target_item.pos()
            self._drop_indicator.setGeometry(
                0, target_pos.y() - 1, self.width(), 2
            )
        else:
            # After last item
            if self._items:
                last_item = self._items[-1]
                y = last_item.pos().y() + last_item.height()
                self._drop_indicator.setGeometry(0, y, self.width(), 2)

        self._drop_indicator.show()


__all__ = ["QGripBoxContainer"]
