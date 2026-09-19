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
  support "hold the hotkey, move, release to run".

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
        self._rows: list[tuple[int, MenuItem, int]] = []  # (y, item, height)
        self._title: str = ""
        self._hover: int = -1
        self._trigger_vk: int = 0
        self._parent = parent_popup
        self._child: "MenuPopup | None" = None
        self._child_index: int = -1
        self._cursor_local: QPoint | None = None
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
        self.setFixedSize(width + theme.PADDING * 2, y + theme.PADDING)

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
        self._pie_items = [i for i in self._items if i.clickable or i.is_branch]
        size = int(theme.PIE_RADIUS * 2 + theme.PADDING * 2)
        self._rows = []
        self.setFixedSize(size, size)

    def _pie_metrics(self) -> tuple[float, float, float, float]:
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_out = float(theme.PIE_RADIUS)
        return cx, cy, r_out, float(theme.PIE_DEAD_ZONE)

    def _segment_mid_angle(self, index: int) -> float:
        """Angle of a segment's centre: 0 deg = straight up, increasing clockwise.

        Both the painter and the hit test go through this one convention, so the
        wedge you point at is the wedge that lights up.
        """
        span = 360.0 / max(1, len(self._pie_items))
        return (index + 0.5) * span

    def _segment_centre(self, index: int, radius: float | None = None) -> QPoint:
        """Widget coordinates of a segment's centre (used for the pointer, dots)."""
        cx, cy, r_out, r_in = self._pie_metrics()
        if radius is None:
            radius = (r_in + r_out) / 2.0
        angle = math.radians(self._segment_mid_angle(index))
        return QPoint(int(cx + math.sin(angle) * radius),
                      int(cy - math.cos(angle) * radius))

    def _pie_index_at(self, pos: QPoint) -> int:
        items = self._pie_items
        if not items:
            return -1
        cx, cy, r_out, r_in = self._pie_metrics()
        dx, dy = pos.x() - cx, pos.y() - cy
        distance = math.hypot(dx, dy)
        if distance < r_in or distance > r_out:
            return -1  # the hole cancels, outside the ring is nothing
        span = 360.0 / len(items)
        angle = (math.degrees(math.atan2(dx, -dy))) % 360.0  # 0 = up, clockwise
        return min(len(items) - 1, int(angle // span))

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
        for idx, (y, _item, h) in enumerate(self._rows):
            if y <= pos.y() < y + h:
                return idx
        return -1

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
            # Beside the segment, in its own direction, then kept on screen.
            cx, cy, r_out, _r_in = self._pie_metrics()
            angle = math.radians(self._segment_mid_angle(index))
            reach = r_out + 6
            x = self.x() + cx + math.sin(angle) * reach
            y = self.y() + cy - math.cos(angle) * reach - child.height() / 2.0
            x = max(area.left(), min(x, area.right() - child.width()))
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
        """Radial layout, Blender-style: wedges run from a small dead zone to the rim.

        Blender's own numbers (pie_menu_radius 100, pie_menu_threshold 12) mean
        there is no centre disc and no centre caption: the wedges meet near the
        middle and leave a 12px hole that selects nothing.
        """
        items = self._pie_items
        cx, cy, r_out, r_in = self._pie_metrics()
        outer = QRectF(cx - r_out, cy - r_out, r_out * 2, r_out * 2)
        inner = QRectF(cx - r_in, cy - r_in, r_in * 2, r_in * 2)

        if items:
            span = 360.0 / len(items)
            label_font = QFont(self._font)
            label_font.setPointSize(theme.PIE_LABEL_SIZE)
            metrics = QFontMetrics(label_font)
            label_radius = r_in + (r_out - r_in) * 0.68
            # Keep each label inside its own wedge: whichever is narrower, a share
            # of the radius or of the arc at that radius. Blender clips labels the
            # same way, but it ships a 100px pie for short English labels - ours
            # sits a bit further out so 8 rows still read.
            arc_width = 2.0 * math.pi * label_radius / len(items)
            half_width = min(r_out * 0.34, arc_width * 0.50)
            dot_radius = min(label_radius + 18.0, r_out - 12.0)

            for index, item in enumerate(items):
                # Qt measures angles anticlockwise with 0 at 3 o'clock; our
                # convention is 0 = up, clockwise, so flip and offset here - the
                # same maths the hit test uses.
                start_qt = 90.0 - index * span
                sweep = span - theme.PIE_GAP_DEG
                path = QPainterPath()
                path.arcMoveTo(outer, start_qt)
                path.arcTo(outer, start_qt, -sweep)
                path.arcTo(inner, start_qt - sweep, sweep)
                path.closeSubpath()

                highlighted = index == self._hover and (item.clickable or item.is_branch)
                painter.setPen(Qt.NoPen)
                if highlighted:
                    painter.setBrush(QColor(*theme.HOVER_BG))
                else:
                    painter.setBrush(QColor(*theme.SEGMENT_BG))
                painter.drawPath(path)

                centre = self._segment_centre(index, label_radius)
                painter.setFont(label_font)
                if highlighted:
                    painter.setPen(QColor(*theme.HOVER_TEXT))
                elif item.enabled:
                    painter.setPen(QColor(*theme.TEXT))
                else:
                    painter.setPen(QColor(*theme.TEXT_DIM))
                box = QRectF(centre.x() - half_width, centre.y() - 9,
                             half_width * 2, 18)
                text = metrics.elidedText(item.label or item.cid, Qt.ElideMiddle,
                                          int(box.width()))
                painter.drawText(box, Qt.AlignCenter, text)

                if item.is_branch:
                    # A dot in the accent colour instead of a glyph: no font
                    # dependency, and it reads as "there is more this way".
                    dot = self._segment_centre(index, dot_radius)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(*theme.ACCENT))
                    painter.drawEllipse(QPointF(dot.x(), dot.y()), 2.5, 2.5)

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
                # across segments on the way to your target.
                if self._child is None or self._child_index != idx:
                    self._dwell.start()
            else:
                self._open_child(idx)
        else:
            self._dwell.stop()
            if self._child is not None:
                self._close_child()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        idx = self._index_at_pos(self._event_pos(event))
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

    def _on_poll(self) -> None:
        """Per-frame health check: Escape cancels, release-of-trigger runs."""
        try:
            if self.is_child:
                return
            if not system.foreground_is_current_process():
                # The user switched to another application - don't linger on top.
                self.dismiss()
                return
            self._sync_cursor()
            if is_key_down(VK_ESCAPE):
                self.dismiss()
                return
            if self._trigger_vk and not is_key_down(self._trigger_vk):
                item = self._deepest_hover()
                self.dismiss()
                if item is not None:
                    run_item(item)
        except Exception:
            log("popup.poll failed", exc=True)
            self.dismiss()

    def set_trigger_vk(self, vk: int) -> None:
        """Remember which held key should run the highlighted row on release."""
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
    ) -> None:
        """Show (or refresh) the overlay at *anchor* (defaults to the cursor).

        *mode* picks the layout: ``LIST`` (vertical rows) or ``PIE`` (radial).
        """
        try:
            self._ensure_app()
            if self._popup is None:
                self._popup = MenuPopup()

            popup = self._popup
            popup.set_mode(mode)

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
