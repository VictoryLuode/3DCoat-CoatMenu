"""
CoatMenu - the popup itself.

A frameless, always-on-top overlay showing a linear list of actions at the
cursor, with submenus opening as further panels beside the hovered row.
Deliberately *not* a normal window:

* ``Qt.ToolTip | FramelessWindowHint | WindowStaysOnTopHint`` - no title bar, no
  taskbar entry, never steals activation from 3DCoat.
* Keyboard is read by polling ``GetAsyncKeyState`` (Win32) instead of
  ``grabKeyboard()``. Grabbing the keyboard from inside 3DCoat swallows the
  user's keys (3DCoat misses the OS key-up), so polling is the only safe way to
  support "press the hotkey once, then click an entry".

Everything is wrapped in try/except: this code runs inside 3DCoat's process, so
a raised exception here is a crash there.
"""
from __future__ import annotations

import ctypes
import math

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from coatmenu.core.log import log
from coatmenu.core.menu_model import (  # noqa: F401  (re-exported for callers/tests)
    COMMAND,
    HEADER,
    LIST,
    PIE,
    SCRIPT,
    SEPARATOR,
    SUBMENU,
    TITLE,
    MenuItem,
    header,
    separator,
    submenu,
    title_item,
)
from coatmenu.ui import cursor as cursor_tool
from coatmenu.ui import system
from coatmenu.ui import theme

# ---------------------------------------------------------------------------
# Win32 key polling
# ---------------------------------------------------------------------------

VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01
VK_RETURN = 0x0D
VK_UP = 0x26
VK_DOWN = 0x28
VK_1 = 0x31  # .. VK_9 = 0x39, the digit row (Blender's pie shortcut keys)


def _user32():
    try:
        return ctypes.windll.user32
    except Exception:
        return None


def is_key_down(vk: int) -> bool:
    """True while the given virtual key is held."""
    u = _user32()
    if u is None or not vk:
        return False
    try:
        return bool(u.GetAsyncKeyState(int(vk)) & 0x8000)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Is the real mouse pointer even visible? (see coatmenu/ui/cursor.py)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The widget
# ---------------------------------------------------------------------------


class MenuPopup(QWidget):
    """Frameless overlay drawing a vertical list of :class:`MenuItem`."""

    def __init__(self, parent_popup: "MenuPopup | None" = None, mode: str = LIST) -> None:
        super().__init__(None)
        self._mode = mode if mode in (LIST, PIE) else LIST
        self._items: list[MenuItem] = []
        self._pie_items: list[MenuItem] = []
        self._pie_rects: list[list[QRectF]] = []      # one list of buttons per slot
        self._pie_targets: list[list[MenuItem]] = []  # parallel to _pie_rects
        self._pie_expanded: list[bool] = []           # slot draws its children in place
        self._slot_distance: float = float(theme.PIE_SLOT_DISTANCE)
        self._rows: list[tuple[int, MenuItem, int]] = []  # (y, item, height)
        self._title: str = ""
        self._hover: int = -1
        self._trigger_vk: int = 0
        self._transient: bool = True
        self._parent = parent_popup
        self._child: "MenuPopup | None" = None
        self._child_index: int = -1
        self._cursor_local: QPoint | None = None
        self._scroll = 0
        self._scroll_max = 0
        self._content_height = 0
        self._keys_down: dict[int, bool] = {}
        self._dwell = QTimer(self)
        self._dwell.setSingleShot(True)
        self._dwell.setInterval(theme.PIE_DWELL_MS)
        self._dwell.timeout.connect(self._on_dwell)

        self.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.NoFocus)

        self._font = QFont(theme.FONT_FAMILY, theme.FONT_SIZE) if theme.FONT_FAMILY else QFont()
        self._fm = QFontMetrics(self._font)
        self._bold = QFont(self._font)
        self._bold.setBold(True)
        self._bold_fm = QFontMetrics(self._bold)

        self._poll = QTimer(self)
        self._poll.setInterval(theme.POLL_MS)
        self._poll.timeout.connect(self._on_poll)

        self._grace = QTimer(self)
        self._grace.setSingleShot(True)
        self._grace.setInterval(theme.SUBMENU_GRACE_MS)
        self._grace.timeout.connect(self._maybe_close_child)

    # -- tree bookkeeping -------------------------------------------------

    @property
    def is_child(self) -> bool:
        return self._parent is not None

    def _root(self) -> "MenuPopup":
        node = self
        while node._parent is not None:
            node = node._parent
        return node

    def _cancel_grace(self) -> None:
        self._root()._grace.stop()

    def _start_grace(self) -> None:
        root = self._root()
        if root._child is not None:
            root._grace.start()

    def child_panels(self) -> list["MenuPopup"]:
        """This panel plus every open panel below it."""
        out = [self]
        node = self._child
        while node is not None:
            out.append(node)
            node = node._child
        return out

    # -- geometry ---------------------------------------------------------

    def set_items(self, items: list[MenuItem]) -> None:
        self._close_child()
        self._items = list(items)
        if self._mode == PIE:
            self._rebuild_pie()
        else:
            self._rebuild_rows()
        self._hover = self._first_interactive()

    def set_title(self, text: str) -> None:
        """List name.

        A list draws it as its first row; a pie has no centre caption (Blender
        does not draw one either) - the title is kept for tooltips and callers.
        """
        self._title = text or ""

    def set_transient(self, transient: bool) -> None:
        """A preview panel never closes itself - the editor owns its lifetime."""
        self._transient = bool(transient)

    def _rebuild_rows(self) -> None:
        rows: list[tuple[int, MenuItem, int]] = []
        y = theme.PADDING
        width = 120
        for item in self._items:
            if item.kind == SEPARATOR:
                h = theme.SEPARATOR_HEIGHT
            elif item.kind == HEADER:
                h = theme.HEADER_HEIGHT
                width = max(width, self._fm.horizontalAdvance(item.label) + theme.ROW_PADDING_H * 2)
            elif item.kind == TITLE:
                h = theme.TITLE_HEIGHT
                width = max(width, self._bold_fm.horizontalAdvance(item.label) + theme.ROW_PADDING_H * 2)
            else:
                h = theme.ROW_HEIGHT
                text = item.label
                width = max(width, self._fm.horizontalAdvance(text) + theme.ROW_PADDING_H * 2
                            + (theme.ARROW_WIDTH + theme.ROW_PADDING_H if item.is_branch else 0))
            rows.append((y, item, h))
            y += h
        self._rows = rows
        self._content_height = y + theme.PADDING
        # Cap the panel: a list longer than the screen scrolls (see wheelEvent and
        # the arrow keys) instead of pushing its last rows out of reach.
        limit = self._viewport_limit()
        self.setFixedSize(width + theme.PADDING * 2, min(self._content_height, limit))
        self._scroll_max = max(0, self._content_height - self.height())
        self._scroll = max(0, min(self._scroll, self._scroll_max))

    def _viewport_limit(self) -> int:
        """Tallest the panel may get - whichever is smaller, our cap or the screen."""
        try:
            screen = QGuiApplication.primaryScreen()
            area = screen.availableGeometry()
            return max(160, min(theme.MAX_MENU_HEIGHT, int(area.height() * 0.85)))
        except Exception:
            return theme.MAX_MENU_HEIGHT

    def _first_interactive(self) -> int:
        """First row the user can act on (a command *or* a submenu).

        The index menu consists only of submenu rows, so "first clickable" would
        leave nothing highlighted and the overlay would look inert. A pie has no
        pre-selection at all: you point at the segment you want.
        """
        if self._mode == PIE:
            return -1
        for idx, (_y, item, _h) in enumerate(self._rows):
            if item.clickable or item.is_branch:
                return idx
        return -1

    # -- pie geometry -----------------------------------------------------

    def _rebuild_pie(self) -> None:
        """Lay the buttons out around the centre - Blender's pie, not a wheel.

        Each slot sits ``PIE_SLOT_DISTANCE`` from the middle in its own direction.
        A slot that is a small group (``PIE_INLINE_MAX`` children or fewer) draws
        its children **stacked in place**, the way Blender's Shading pie shows
        Material/Wireframe; bigger groups still unfold into a child panel.

        Geometry is kept as rects so the painter and the hit test cannot drift.
        """
        self._pie_items = [i for i in self._items if i.clickable or i.is_branch]
        self._rows = []
        self._pie_rects = []
        self._pie_targets = []
        self._pie_expanded = []
        count = len(self._pie_items)
        min_size = int(2 * (theme.PIE_SLOT_DISTANCE + theme.PIE_CENTRE_RING
                            + theme.PADDING))
        if not count:
            self.setFixedSize(min_size, min_size)
            return

        metrics = QFontMetrics(self._font)
        slot_buttons: list[list[MenuItem]] = []
        widths: list[float] = []
        room = theme.PIE_DIGIT_HINT_W + theme.PADDING * 3
        for item in self._pie_items:
            children = list(item.children)
            if item.is_branch and 0 < len(children) <= theme.PIE_INLINE_MAX:
                buttons = children
                self._pie_expanded.append(True)
            else:
                buttons = [item]
                self._pie_expanded.append(False)
            slot_buttons.append(buttons)
            widest = max(metrics.horizontalAdvance(b.label or b.cid or "") for b in buttons)
            widths.append(max(theme.PIE_BUTTON_MIN_W,
                              min(theme.PIE_BUTTON_MAX_W, float(widest + room))))

        step = theme.PIE_SLOT_HEIGHT + theme.PIE_BUTTON_GAP
        heights = [len(buttons) * step - theme.PIE_BUTTON_GAP for buttons in slot_buttons]
        # Push the ring out until neighbouring slots cannot touch: at N slots the
        # distance between two slot centres is 2*R*sin(pi/N), so R has to clear
        # the widest slot. Blender grows its pie the same way.
        gap = math.sin(math.pi / count) if count > 1 else 1.0
        needed = max(widths) / (2.0 * gap) if count > 1 else 0.0
        self._slot_distance = max(float(theme.PIE_SLOT_DISTANCE), needed * 1.06)
        half = max(max(widths) / 2.0, max(heights) / 2.0, theme.PIE_CENTRE_RING / 2.0)
        size = int(2 * (self._slot_distance + half + theme.PADDING))
        self.setFixedSize(size, size)

        cx = cy = size / 2.0
        for index, buttons in enumerate(slot_buttons):
            angle = math.radians(self._slot_angle(index))
            bx = cx + math.sin(angle) * self._slot_distance
            by = cy - math.cos(angle) * self._slot_distance
            width = widths[index]
            top = by - heights[index] / 2.0
            rects = []
            for row_index, _button in enumerate(buttons):
                rects.append(QRectF(bx - width / 2.0, top + row_index * step,
                                    width, float(theme.PIE_SLOT_HEIGHT)))
            self._pie_rects.append(rects)
            self._pie_targets.append(list(buttons))

    def _centre_point(self) -> QPointF:
        return QPointF(self.width() / 2.0, self.height() / 2.0)

    def _slot_angle(self, index: int) -> float:
        """Direction of a slot: 0 deg = straight up, increasing clockwise.

        The painter, the hit test and the submenu placement all use this, so the
        button you point at is the button that lights up.
        """
        span = 360.0 / max(1, len(self._pie_items))
        return (index + 0.5) * span

    def _slot_rects(self, index: int) -> list[QRectF]:
        """Every button rect of one slot (a slot may stack several)."""
        if 0 <= index < len(self._pie_rects):
            return self._pie_rects[index]
        return []

    def _slot_targets(self, index: int) -> list[MenuItem]:
        if 0 <= index < len(self._pie_targets):
            return self._pie_targets[index]
        return []

    def _slot_rect(self, index: int) -> QRectF:
        """Bounding box of a slot - used for placement and for the tests."""
        rects = self._slot_rects(index)
        if not rects:
            return QRectF()
        box = QRectF(rects[0])
        for rect in rects[1:]:
            box = box.united(rect)
        return box

    def _slot_centre(self, index: int) -> QPoint:
        rect = self._slot_rect(index)
        return QPoint(int(rect.center().x()), int(rect.center().y()))

    def _slot_expanded(self, index: int) -> bool:
        return 0 <= index < len(self._pie_expanded) and self._pie_expanded[index]

    def _pie_hit(self, pos: QPoint) -> tuple[int, int] | None:
        """``(slot, button)`` under the point, or None."""
        point = QPointF(pos)
        for slot, rects in enumerate(self._pie_rects):
            for button, rect in enumerate(rects):
                if rect.contains(point):
                    return slot, button
        return None

    def _pie_index_at(self, pos: QPoint) -> int:
        hit = self._pie_hit(pos)
        return hit[0] if hit is not None else -1

    def _pie_click_item(self, pos: QPoint) -> tuple[int, MenuItem] | None:
        """The item a click at *pos* should act on (slot index + item)."""
        hit = self._pie_hit(pos)
        if hit is None:
            return None
        slot, button = hit
        targets = self._slot_targets(slot)
        if not (0 <= button < len(targets)):
            return None
        return slot, targets[button]

    def _item_at_index(self, index: int) -> MenuItem | None:
        if self._mode == PIE:
            return self._pie_items[index] if 0 <= index < len(self._pie_items) else None
        return self._rows[index][1] if 0 <= index < len(self._rows) else None

    def _index_at_pos(self, pos: QPoint) -> int:
        if self._mode == PIE:
            return self._pie_index_at(pos)
        return self._row_at(pos)

    def _count_items(self) -> int:
        return len(self._pie_items) if self._mode == PIE else len(self._rows)

    def _first_branch(self) -> int:
        if self._mode == PIE:
            for idx, item in enumerate(self._pie_items):
                if item.is_branch:
                    return idx
            return -1
        for idx, (_y, item, _h) in enumerate(self._rows):
            if item.is_branch:
                return idx
        return -1

    def set_mode(self, mode: str) -> None:
        """Switch list <-> pie (the widget survives, its layout is rebuilt)."""
        mode = mode if mode in (LIST, PIE) else LIST
        if mode != self._mode:
            self._close_child()
            self._mode = mode

    def _row_at(self, pos: QPoint) -> int:
        y_pos = pos.y() + self._scroll
        for idx, (y, _item, h) in enumerate(self._rows):
            if y <= y_pos < y + h:
                return idx
        return -1

    def _ensure_visible(self, index: int) -> None:
        """Scroll so the given row is inside the panel (keyboard navigation)."""
        if not self._scroll_max or not (0 <= index < len(self._rows)):
            return
        y, _item, h = self._rows[index]
        top = theme.PADDING
        bottom = self.height() - theme.PADDING
        if y < self._scroll + top:
            self._scroll = max(0, y - top)
        elif y + h > self._scroll + bottom:
            self._scroll = min(self._scroll_max, y + h - bottom)

    @staticmethod
    def _event_pos(event) -> QPoint:
        """Cursor position of a Qt mouse event (QPointF on Qt6)."""
        point = event.position()
        if hasattr(point, "toPoint"):
            return point.toPoint()
        return QPoint(int(point.x()), int(point.y()))

    # -- submenus ---------------------------------------------------------

    def _open_child(self, index: int) -> None:
        """Open (or re-target) the child panel for a branch row/segment."""
        try:
            item = self._item_at_index(index)
            if item is None or not item.is_branch:
                self._close_child()
                return
            if self._child is not None and self._child_index == index and self._child.isVisible():
                return
            self._close_child()
            if not item.children:
                return

            child = MenuPopup(parent_popup=self)
            child.set_items(item.children)
            # Nothing is highlighted until the cursor actually enters the child,
            # otherwise it would look like release-to-run would fire that row.
            child._hover = -1
            child.setWindowOpacity(1.0)
            child.show()
            child.move(self._child_position(index, child))
            child.update()
            self._child = child
            self._child_index = index
            self._grace.stop()
            self.update()
        except Exception:
            log("popup._open_child failed", exc=True)

    def _on_dwell(self) -> None:
        """Pie only: open a branch's submenu once the cursor rests on it."""
        try:
            if self._mode != PIE or self._hover < 0:
                return
            if self._slot_expanded(self._hover):
                return  # the children are already on screen
            item = self._item_at_index(self._hover)
            if item is not None and item.is_branch:
                self._open_child(self._hover)
        except Exception:
            log("popup dwell failed", exc=True)

    def _child_position(self, index: int, child: "MenuPopup") -> QPoint:
        screen = QGuiApplication.screenAt(QPoint(self.x() + 10, self.y() + 10)) \
            or QGuiApplication.primaryScreen()
        try:
            area = screen.availableGeometry()
        except AttributeError:
            area = screen.geometry()

        if self._mode == PIE:
            # Next to its button, on the side pointing away from the centre.
            anchor = self._slot_centre(index)
            outward = 26
            if anchor.x() >= self.width() / 2.0:
                x = self.x() + anchor.x() + outward
                x = min(x, area.right() - child.width())
            else:
                x = self.x() + anchor.x() - outward - child.width()
                x = max(x, area.left())
            y = self.y() + anchor.y() - child.height() / 2.0
            y = max(area.top(), min(y, area.bottom() - child.height()))
            return QPoint(int(x), int(y))

        row_y = self._rows[index][0]
        x = self.x() + self.width() - theme.SUBMENU_OVERLAP
        if x + child.width() > area.right():
            x = self.x() - child.width() + theme.SUBMENU_OVERLAP
        # Align the child's first row with the parent row it belongs to, so the
        # two panels read as one menu (PADDING is the panel's inner margin).
        y = self.y() + row_y - theme.PADDING
        if y + child.height() > area.bottom():
            y = max(area.top(), area.bottom() - child.height())
        return QPoint(int(x), int(y))

    def _close_child(self) -> None:
        child = self._child
        self._child = None
        self._child_index = -1
        if child is not None:
            child.dismiss()
        self.update()

    def _maybe_close_child(self) -> None:
        child = self._child
        if child is None:
            return
        try:
            if child.underMouse():
                return
        except Exception:
            pass
        self._close_child()

    def _deepest_hover(self) -> MenuItem | None:
        """Row the user is really pointing at, following visible child panels."""
        popup: MenuPopup | None = self
        found: MenuItem | None = None
        while popup is not None:
            candidate = popup._item_at_index(popup._hover)
            if candidate is not None and candidate.clickable:
                found = candidate
            child = popup._child
            if child is None or not child.isVisible():
                break
            try:
                if not child.underMouse():
                    break
            except Exception:
                break
            popup = child
        return found

    # -- painting ---------------------------------------------------------

    def _draw_cursor(self, painter: QPainter) -> None:
        """Draw our own pointer when 3DCoat has hidden the system one."""
        cursor_tool.draw(painter, self._cursor_local)

    def _sync_cursor(self) -> None:
        """Follow the real pointer position (driven by the poll timer).

        Needed because a hidden system cursor gives no feedback at all: the mouse
        can sit still, and the overlay still has to show where it is.
        """
        for panel in self.child_panels():
            value = cursor_tool.local_position(panel)
            if value != panel._cursor_local:
                panel._cursor_local = value
                panel.update()

    def _draw_arrow(self, painter: QPainter, centre_y: float, colour: QColor) -> None:
        """Right-pointing triangle for submenu rows.

        Drawn rather than typed: Unicode ▸ is missing from plenty of fonts and
        would show up as a tofu box.
        """
        tip_x = self.width() - theme.ROW_PADDING_H - 3
        path = QPainterPath()
        path.moveTo(tip_x - theme.ARROW_WIDTH, centre_y - theme.ARROW_HEIGHT / 2.0)
        path.lineTo(tip_x, centre_y)
        path.lineTo(tip_x - theme.ARROW_WIDTH, centre_y + theme.ARROW_HEIGHT / 2.0)
        path.closeSubpath()
        painter.fillPath(path, colour)

    def _draw_pie(self, painter: QPainter) -> None:
        """Blender-style pie: rounded buttons around a small centre ring.

        Not a wheel of wedges - Blender lays ordinary buttons out radially and
        paints a ring where the cursor sits, with the shortcut digit on each
        button. Same rects the hit test uses.
        """
        ring_radius = theme.PIE_CENTRE_RING / 2.0
        painter.setPen(QPen(QColor(*theme.BORDER), 2))
        painter.setBrush(QColor(*theme.BG))
        painter.drawEllipse(self._centre_point(), ring_radius, ring_radius)

        label_font = QFont(self._font)
        label_font.setPointSize(theme.PIE_LABEL_SIZE)
        metrics = QFontMetrics(label_font)
        hint_font = QFont(self._font)
        hint_font.setPointSize(max(6, theme.PIE_LABEL_SIZE - 3))

        for index, item in enumerate(self._pie_items):
            slot_rects = self._slot_rects(index)
            targets = self._slot_targets(index)
            highlighted = index == self._hover and (item.clickable or item.is_branch)
            for button_index, rect in enumerate(slot_rects):
                target = targets[button_index] if button_index < len(targets) else item
                enabled = target.enabled and target.clickable
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(*(theme.HOVER_BG if highlighted else theme.SEGMENT_BG)))
                painter.drawRoundedRect(rect, theme.PIE_BUTTON_RADIUS, theme.PIE_BUTTON_RADIUS)

                painter.setFont(label_font)
                if highlighted:
                    painter.setPen(QColor(*theme.HOVER_TEXT))
                elif enabled:
                    painter.setPen(QColor(*theme.TEXT))
                else:
                    painter.setPen(QColor(*theme.TEXT_DIM))
                # The digit belongs to the slot, so only its first button shows it.
                hint = str(index + 1) if (button_index == 0 and index < 9) else ""
                room = float(theme.PIE_DIGIT_HINT_W) if hint else 0.0
                text_box = QRectF(rect.left() + theme.PADDING, rect.top(),
                                  max(10.0, rect.width() - room - theme.PADDING * 2),
                                  rect.height())
                text = metrics.elidedText(target.label or target.cid, Qt.ElideMiddle,
                                          int(text_box.width()))
                painter.drawText(text_box, Qt.AlignCenter, text)

                if hint:
                    # Blender prints the shortcut digit on the button; here it is
                    # the 1..9 key that runs this slot while the menu is open.
                    painter.setFont(hint_font)
                    painter.setPen(QColor(*(theme.HOVER_TEXT if highlighted else theme.TEXT_DIM)))
                    hint_box = QRectF(rect.right() - theme.PADDING - room, rect.top(),
                                      room, rect.height())
                    painter.drawText(hint_box, Qt.AlignCenter, hint)

                if button_index == 0 and item.is_branch and not self._slot_expanded(index):
                    # A dot in the accent colour instead of a glyph: no font
                    # dependency, and it reads as "there is more this way".
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(*theme.ACCENT))
                    painter.drawEllipse(QPointF(rect.left() + 4.0, rect.top() + 4.0),
                                        2.5, 2.5)

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

            if self._mode == PIE:
                self._draw_pie(painter)
                self._draw_cursor(painter)
                return

            rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
            painter.setPen(QPen(QColor(*theme.BORDER), theme.BORDER_WIDTH))
            painter.setBrush(QColor(*theme.BG))
            painter.drawRoundedRect(rect, theme.CORNER_RADIUS, theme.CORNER_RADIUS)

            # A scrolling list: rows are drawn at their unscrolled y, shifted here.
            clipped = self._scroll_max > 0
            if clipped:
                painter.save()
                painter.setClipRect(QRectF(0, theme.PADDING, self.width(),
                                           self.height() - theme.PADDING * 2))
                painter.translate(0, -self._scroll)

            for idx, (y, item, h) in enumerate(self._rows):
                if item.kind == SEPARATOR:
                    painter.setPen(QPen(QColor(*theme.SEPARATOR), 1))
                    painter.drawLine(
                        theme.PADDING, y + h // 2, self.width() - theme.PADDING, y + h // 2
                    )
                    continue

                if item.kind == HEADER:
                    painter.setFont(self._bold)
                    painter.setPen(QColor(*theme.TEXT_DIM))
                    painter.drawText(
                        theme.ROW_PADDING_H,
                        y,
                        self.width() - theme.ROW_PADDING_H * 2,
                        h,
                        Qt.AlignVCenter | Qt.AlignLeft,
                        item.label,
                    )
                    continue

                if item.kind == TITLE:
                    painter.setFont(self._bold)
                    painter.setPen(QColor(*theme.ACCENT))
                    painter.drawText(
                        theme.ROW_PADDING_H,
                        y,
                        self.width() - theme.ROW_PADDING_H * 2,
                        h,
                        Qt.AlignVCenter | Qt.AlignLeft,
                        item.label,
                    )
                    painter.setPen(QPen(QColor(*theme.SEPARATOR), 1))
                    painter.drawLine(
                        theme.PADDING,
                        y + h - 2,
                        self.width() - theme.PADDING,
                        y + h - 2,
                    )
                    continue

                highlighted = idx == self._hover and (item.clickable or item.is_branch)
                if highlighted:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(*theme.HOVER_BG))
                    painter.drawRoundedRect(
                        QRectF(
                            theme.PADDING * 0.5,
                            y,
                            self.width() - theme.PADDING,
                            h,
                        ),
                        theme.ROW_CORNER_RADIUS,
                        theme.ROW_CORNER_RADIUS,
                    )

                painter.setFont(self._font)
                if highlighted:
                    painter.setPen(QColor(*theme.HOVER_TEXT))
                elif item.enabled:
                    painter.setPen(QColor(*theme.TEXT))
                else:
                    painter.setPen(QColor(*theme.TEXT_DIM))

                text = item.label
                painter.drawText(
                    theme.ROW_PADDING_H,
                    y,
                    self.width() - theme.ROW_PADDING_H * 2,
                    h,
                    Qt.AlignVCenter | Qt.AlignLeft,
                    text,
                )
                if item.is_branch:
                    self._draw_arrow(
                        painter,
                        y + h / 2.0,
                        QColor(*theme.HOVER_TEXT) if highlighted else QColor(*theme.TEXT_DIM),
                    )

            if clipped:
                painter.restore()
                self._draw_scrollbar(painter)

            self._draw_cursor(painter)
        except Exception:
            log("popup.paintEvent failed", exc=True)
        finally:
            painter.end()

    # -- input ------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._cancel_grace()
        pos = self._event_pos(event)
        self._cursor_local = pos
        idx = self._index_at_pos(pos)
        if idx != self._hover:
            self._hover = idx
            self.update()
        item = self._item_at_index(idx)
        if item is None:
            self._dwell.stop()
            self._close_child()
            return
        if item.is_branch:
            if self._mode == PIE:
                # Let the cursor settle before unfolding: in a pie you sweep
                # across slots on the way to your target. A slot that draws its
                # children in place has nothing left to unfold.
                if not self._slot_expanded(idx) and (
                        self._child is None or self._child_index != idx):
                    self._dwell.start()
            else:
                self._open_child(idx)
        else:
            self._dwell.stop()
            if self._child is not None:
                self._close_child()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = self._event_pos(event)
        if self._mode == PIE:
            hit = self._pie_click_item(pos)
            if hit is None:
                self._root().dismiss()
                return
            slot, item = hit
            if item.is_branch and not self._slot_expanded(slot):
                self._open_child(slot)  # a big group still unfolds into a panel
                return
            if not item.clickable:
                self._root().dismiss()
                return
            self._root().dismiss()
            run_item(item)
            return

        idx = self._index_at_pos(pos)
        item = self._item_at_index(idx)
        if item is None:
            self._root().dismiss()
            return
        if item.is_branch:
            self._open_child(idx)
            return
        if not item.clickable:
            # headers and separators are not click targets: clicking one closes
            self._root().dismiss()
            return
        self._root().dismiss()
        run_item(item)

    def leaveEvent(self, _event) -> None:  # noqa: N802
        self._hover = self._first_interactive()
        self._cursor_local = None
        self.update()
        self._start_grace()

    def enterEvent(self, _event) -> None:  # noqa: N802
        self._cancel_grace()
        try:
            from PySide6.QtGui import QCursor
            local = self.mapFromGlobal(QCursor.pos())
            self._cursor_local = local if self.rect().contains(local) else None
        except Exception:
            self._cursor_local = None

    # -- lifecycle --------------------------------------------------------

    def show_at(self, anchor: QPoint, trigger_vk: int = 0) -> None:
        """Show at *anchor* (screen coords), clamped to the screen."""
        self.set_trigger_vk(trigger_vk)
        self._close_child()
        pos = self._clamped_position(anchor)
        self.move(pos)
        self.setWindowOpacity(0.0 if theme.FADE_IN else 1.0)
        self.show()
        self.update()
        if theme.FADE_IN:
            self._fade_tick()
        if not self.is_child:
            self._poll.start()

    def _clamped_position(self, anchor: QPoint) -> QPoint:
        """Panel top-left sits exactly on the anchor - same as Krita's QMenu.

        Flips to the other side of the cursor when the panel would otherwise run
        off the screen.
        """
        x, y = anchor.x(), anchor.y()
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        try:
            area = screen.availableGeometry()
        except AttributeError:
            area = screen.geometry()
        if x + self.width() > area.right():
            x = max(area.left(), anchor.x() - self.width())
        if y + self.height() > area.bottom():
            y = max(area.top(), anchor.y() - self.height())
        return QPoint(int(x), int(y))

    def _fade_tick(self) -> None:
        step = 0.22
        value = min(1.0, self.windowOpacity() + step)
        self.setWindowOpacity(value)
        if value < 1.0 and self.isVisible():
            QTimer.singleShot(theme.FADE_MS // 5, self._fade_tick)

    def _click_outside(self, pos: QPoint | None = None) -> bool:
        """True when the left button is down somewhere outside our panels.

        The overlay never grabs the mouse (that would stop 3DCoat seeing clicks),
        so a click away from the menu has to be noticed by polling - that click
        still reaches 3DCoat and the menu simply closes, as in Blender.
        """
        if not is_key_down(VK_LBUTTON):
            return False
        if pos is None:
            try:
                from PySide6.QtGui import QCursor

                pos = QCursor.pos()
            except Exception:
                return False
        for panel in self.child_panels():
            if panel.isVisible() and panel.frameGeometry().contains(pos):
                return False
        return True

    def _poll_keys(self) -> None:
        """Arrow keys move the highlight; Enter opens a group or runs the entry.

        Edge-triggered: the keys are read by polling, so a held key must not race
        through the whole list.
        """
        for vk, delta in ((VK_DOWN, 1), (VK_UP, -1)):
            down = is_key_down(vk)
            if down and not self._keys_down.get(vk):
                self._move_hover(delta)
            self._keys_down[vk] = down

        enter = is_key_down(VK_RETURN)
        if enter and not self._keys_down.get(VK_RETURN):
            self._activate_hover()
        self._keys_down[VK_RETURN] = enter

    def _move_hover(self, delta: int) -> None:
        """Move the highlight to the next actionable row / slot."""
        count = len(self._pie_items) if self._mode == PIE else len(self._rows)
        if not count:
            return
        index = self._hover
        for _step in range(count):
            index = (index + delta) % count
            if self._is_actionable(index):
                self._hover = index
                self._ensure_visible(index)
                self.update()
                return

    def _activate_hover(self) -> None:
        """Enter: unfold a group, otherwise run the highlighted entry."""
        index = self._hover
        item = self._item_at_index(index)
        if item is None:
            return
        if item.is_branch and not (self._mode == PIE and self._slot_expanded(index)):
            self._open_child(index)
            return
        if item.clickable:
            self.dismiss()
            run_item(item)

    def _is_actionable(self, index: int) -> bool:
        item = self._item_at_index(index)
        return item is not None and (item.clickable or item.is_branch)

    def _digit_target(self, index: int) -> MenuItem | None:
        """The entry the N-th digit points at (slot in a pie, row in a list)."""
        if self._mode == PIE:
            targets = self._slot_targets(index)
            return targets[0] if targets else None
        actionable = [i for i in range(len(self._rows)) if self._is_actionable(i)]
        if index >= len(actionable):
            return None
        return self._item_at_index(actionable[index])

    def _check_digits(self) -> bool:
        """The 1..9 keys run the N-th entry.

        In a pie the digit is printed on the slot button (Blender's shortcut); in
        a list it is the N-th actionable row - not printed, to stay close to
        3DCoat's own menu look.
        """
        for index in range(min(9, self._count_items())):
            if is_key_down(VK_1 + index):
                item = self._digit_target(index)
                self.dismiss()
                if item is not None and item.clickable:
                    run_item(item)
                return True
        return False

    def _draw_scrollbar(self, painter: QPainter) -> None:
        """Thin indicator on the right: this panel holds more than it shows."""
        track_h = self.height() - theme.PADDING * 2
        if track_h <= 0 or self._content_height <= 0 or not self._scroll_max:
            return
        thumb_h = max(24.0, track_h * self.height() / self._content_height)
        travel = max(0.0, track_h - thumb_h)
        top = theme.PADDING + travel * (self._scroll / self._scroll_max)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*theme.BORDER))
        painter.drawRoundedRect(
            QRectF(self.width() - theme.PADDING - theme.SCROLLBAR_W + 1, top,
                   float(theme.SCROLLBAR_W), thumb_h),
            1.5, 1.5,
        )

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Mouse wheel scrolls a long list (a pie never scrolls)."""
        if self._mode == PIE or not self._scroll_max:
            return
        steps = event.angleDelta().y() / 120.0
        self._scroll = max(0, min(self._scroll_max,
                                  int(self._scroll - steps * theme.ROW_HEIGHT * 2)))
        self.update()

    def _on_poll(self) -> None:
        """Per-frame health check: Escape and clicks outside close the menu.

        The menu stays put when the hotkey is released - it closes when you pick
        something, click away, or press Escape.
        """
        try:
            if self.is_child:
                return
            if not self._transient:
                # A preview shown by the editor: it stays until the editor closes
                # it, and it never runs anything (no digit keys, no click-away).
                self._sync_cursor()
                return
            if not system.foreground_is_current_process():
                # The user switched to another application - don't linger on top.
                self.dismiss()
                return
            self._sync_cursor()
            if is_key_down(VK_ESCAPE):
                self.dismiss()
                return
            self._poll_keys()
            if self._check_digits():
                return
            if self._click_outside():
                self.dismiss()
        except Exception:
            log("popup.poll failed", exc=True)
            self.dismiss()

    def set_trigger_vk(self, vk: int) -> None:
        """Remember the key that opened the menu.

        Kept for callers (the hotkey id that fired is still useful in logs), but
        releasing it no longer runs or closes anything.
        """
        self._trigger_vk = int(vk or 0)

    def dismiss(self) -> None:
        """Close this panel and every panel below it, running nothing."""
        try:
            self._poll.stop()
            self._grace.stop()
            self._close_child()
            self.hide()
            self._trigger_vk = 0
            self.setWindowOpacity(1.0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


def run_item(item: MenuItem) -> None:
    """Execute one menu entry (never raises)."""
    try:
        import coat  # type: ignore
    except Exception as exc:
        log(f"run_item: coat import failed: {exc}")
        return
    try:
        if item.cmds:
            # Multi-step action: same frame, same order 3DCoat's own UI uses.
            for raw in item.cmds:
                cmd = raw if raw.startswith("$") else "$" + raw
                coat.ui.cmd(cmd)
            log(f"ran sequence: {item.cmds}")
        elif item.kind == SCRIPT:
            coat.io.executeScript(item.path or item.cid)
            log(f"ran script: {item.path or item.cid}")
        else:
            cmd = item.cid if item.cid.startswith("$") else "$" + item.cid
            coat.ui.cmd(cmd)
            log(f"ran command: {cmd}")
    except Exception as exc:
        log(f"run_item failed ({item.kind} {item.cid}): {exc}", exc=True)


# ---------------------------------------------------------------------------
# Manager (singleton - one overlay per process)
# ---------------------------------------------------------------------------


class PopupManager:
    """Owns the top-level overlay instance and its Qt bootstrap."""

    def __init__(self) -> None:
        self._popup: MenuPopup | None = None
        self._app = None

    def _ensure_app(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        self._app = app
        return app

    @property
    def popup(self) -> MenuPopup | None:
        return self._popup

    def set_transient(self, transient: bool) -> None:
        """Forward to the overlay (a preview panel never closes itself)."""
        if self._popup is not None:
            self._popup.set_transient(transient)

    def is_visible(self) -> bool:
        try:
            return bool(self._popup and self._popup.isVisible())
        except Exception:
            return False

    def show_menu(
        self,
        items: list[MenuItem],
        anchor: QPoint | None = None,
        trigger_vk: int = 0,
        title: str = "",
        mode: str = LIST,
        transient: bool = True,
    ) -> None:
        """Show (or refresh) the overlay at *anchor* (defaults to the cursor).

        *mode* picks the layout: ``LIST`` (vertical rows) or ``PIE`` (radial).
        ``transient=False`` is for the editor's preview: such a panel stays put
        until it is dismissed explicitly and never runs anything.
        """
        try:
            self._ensure_app()
            if self._popup is None:
                self._popup = MenuPopup()

            popup = self._popup
            popup.set_mode(mode)
            popup.set_transient(transient)

            show_items = list(items)
            if title and mode != PIE:
                # A list shows its name as a title row; a pie paints it in the hole.
                show_items = [title_item(title)] + show_items

            if popup.isVisible():
                popup.set_items(show_items)
                popup.set_title(title)
                popup.set_trigger_vk(trigger_vk)
                popup.update()
                return

            popup.set_items(show_items)
            popup.set_title(title)
            if anchor is None:
                anchor = _cursor_pos()
            popup.show_at(anchor, trigger_vk=trigger_vk)
        except Exception:
            log("show_menu failed", exc=True)

    def hide(self) -> None:
        if self._popup is not None:
            self._popup.dismiss()


def _cursor_pos() -> QPoint:
    """Cursor position in screen coordinates, via 3DCoat when available."""
    try:
        from PySide6.QtGui import QCursor
        return QCursor.pos()
    except Exception:
        return QPoint(200, 200)


_manager: PopupManager | None = None


def get_manager() -> PopupManager:
    global _manager
    if _manager is None:
        _manager = PopupManager()
    return _manager


def show_menu(items: list[MenuItem], anchor: QPoint | None = None,
              trigger_vk: int = 0, title: str = "", mode: str = LIST) -> None:
    get_manager().show_menu(items, anchor=anchor, trigger_vk=trigger_vk, title=title, mode=mode)


def hide_menu() -> None:
    get_manager().hide()


def tick() -> None:
    """Pump Qt events - call this once per frame from the cExtension hook."""
    try:
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
    except Exception:
        pass
