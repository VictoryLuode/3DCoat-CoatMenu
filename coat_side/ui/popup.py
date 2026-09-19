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

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
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

from core.log import log
from core.menu_model import (  # noqa: F401  (re-exported for callers/tests)
    COMMAND,
    HEADER,
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
from ui import theme

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
# The widget
# ---------------------------------------------------------------------------


class MenuPopup(QWidget):
    """Frameless overlay drawing a vertical list of :class:`MenuItem`."""

    def __init__(self, parent_popup: "MenuPopup | None" = None) -> None:
        super().__init__(None)
        self._items: list[MenuItem] = []
        self._rows: list[tuple[int, MenuItem, int]] = []  # (y, item, height)
        self._hover: int = -1
        self._trigger_vk: int = 0
        self._parent = parent_popup
        self._child: "MenuPopup | None" = None
        self._child_row: int = -1

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
        self._rebuild_rows()
        self._hover = self._first_clickable()

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

    def _first_clickable(self) -> int:
        for idx, (_y, item, _h) in enumerate(self._rows):
            if item.clickable:
                return idx
        return -1

    def _first_branch(self) -> int:
        for idx, (_y, item, _h) in enumerate(self._rows):
            if item.is_branch:
                return idx
        return -1

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

    def _open_child(self, row_index: int) -> None:
        """Open (or re-target) the child panel for a branch row."""
        try:
            if row_index < 0 or row_index >= len(self._rows):
                return
            item = self._rows[row_index][1]
            if not item.is_branch:
                self._close_child()
                return
            if self._child is not None and self._child_row == row_index and self._child.isVisible():
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
            child.move(self._child_position(row_index, child))
            child.update()
            self._child = child
            self._child_row = row_index
            self._grace.stop()
            self.update()
        except Exception:
            log("popup._open_child failed", exc=True)

    def _child_position(self, row_index: int, child: "MenuPopup") -> QPoint:
        row_y = self._rows[row_index][0]
        x = self.x() + self.width() - theme.SUBMENU_OVERLAP
        screen = QGuiApplication.screenAt(QPoint(self.x() + 10, self.y() + 10)) \
            or QGuiApplication.primaryScreen()
        try:
            area = screen.availableGeometry()
        except AttributeError:
            area = screen.geometry()
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
        self._child_row = -1
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
            if 0 <= popup._hover < len(popup._rows):
                candidate = popup._rows[popup._hover][1]
                if candidate.clickable:
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

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)

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
                        4,
                        4,
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
        except Exception:
            log("popup.paintEvent failed", exc=True)
        finally:
            painter.end()

    # -- input ------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._cancel_grace()
        idx = self._row_at(self._event_pos(event))
        if idx != self._hover:
            self._hover = idx
            self.update()
        if idx < 0:
            self._close_child()
            return
        if self._rows[idx][1].is_branch:
            self._open_child(idx)
        elif self._child is not None and self._child_row != idx:
            self._close_child()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        idx = self._row_at(self._event_pos(event))
        if idx < 0 or idx >= len(self._rows):
            self._root().dismiss()
            return
        item = self._rows[idx][1]
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
        self._hover = self._first_clickable()
        self.update()
        self._start_grace()

    def enterEvent(self, _event) -> None:  # noqa: N802
        self._cancel_grace()

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
        off = 10
        x, y = anchor.x() + off, anchor.y() + off
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        try:
            area = screen.availableGeometry()
        except AttributeError:
            area = screen.geometry()
        if x + self.width() > area.right():
            x = max(area.left(), anchor.x() - self.width() - off)
        if y + self.height() > area.bottom():
            y = max(area.top(), anchor.y() - self.height() - off)
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
        if item.kind == SCRIPT:
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
    ) -> None:
        """Show (or refresh) the overlay at *anchor* (defaults to the cursor)."""
        try:
            self._ensure_app()
            if self._popup is None:
                self._popup = MenuPopup()

            show_items = list(items)
            if title:
                show_items = [title_item(title)] + show_items

            popup = self._popup
            if popup.isVisible():
                popup.set_items(show_items)
                popup.set_trigger_vk(trigger_vk)
                popup.update()
                return

            popup.set_items(show_items)
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
              trigger_vk: int = 0, title: str = "") -> None:
    get_manager().show_menu(items, anchor=anchor, trigger_vk=trigger_vk, title=title)


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
