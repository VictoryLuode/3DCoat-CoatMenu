"""Collapsible panel widget for PySide6.

`QCollapsiblePanel` keeps a permanent thin ribbon visible and collapses/expands
its content from a chosen edge.

Supported directions:

* ``"right"``: ribbon on left, content expands to the right.
* ``"left"``: ribbon on right, content expands to the left.
* ``"top"``: ribbon on bottom, content expands upward.
* ``"bottom"``: ribbon on top, content expands downward.

The visual style matches the existing side panel language: thin strip,
subtle hover/pressed states, and directional arrow indicating expand/collapse.
"""
from __future__ import annotations

import sys

# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(
            None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from typing import Any

from PySide6.QtCore import QEasingCurve, QPointF, QRect, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ── Visual constants ──────────────────────────────────────────────────────────
_STRIP_WIDTH: int = 22          # thin ribbon — wide enough for rotated 9pt text
_ARROW_ZONE: int = 22           # height of the arrow zone at the top of the ribbon
_ARROW_SIZE: int = 8
_TEXT_PADDING: int = 6          # gap between icon/arrow zone and start of text run
_ICON_SIZE: int = 14            # square icon drawn between arrow zone and text
_PANEL_ANIM_MS: int = 180       # collapse / expand animation duration (ms)
_HANDLE_WIDTH: int = 4          # width of the resize drag handle
_DEFAULT_CONTENT_WIDTH: int = 260   # initial content width when no saved state
_DEFAULT_CONTENT_HEIGHT: int = 220  # initial content height for top/bottom panels
_MIN_CONTENT_WIDTH: int = 60    # floor for content resize drag
_MAX_CONTENT_WIDTH: int = 1200  # ceiling for content resize drag
_MIN_CONTENT_HEIGHT: int = 48
_MAX_CONTENT_HEIGHT: int = 1400

# Grayscale palette — shared look with QCollapsibleSection
_BG_NORMAL: str = "#353535"
_BG_HOVER: str = "#404040"
_BG_PRESSED: str = "#2e2e2e"
_BORDER_COLOR: str = "#4a4a4a"
_TEXT_COLOR: str = "#d0d0d0"
_ARROW_COLOR: str = _TEXT_COLOR
_HANDLE_IDLE: str = "#282828"
_HANDLE_HOVER: str = "#555555"
_HANDLE_DRAG: str = "#6699cc"


# ── _ResizeHandle ─────────────────────────────────────────────────────────────


class _ResizeHandle(QWidget):
    """Thin draggable bar for resizing the panel content span.

    For left/right panels, span is width and drag axis is horizontal.
    For top/bottom panels, span is height and drag axis is vertical.
    """

    def __init__(
        self,
        expand_direction: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expand_direction = expand_direction
        self._content: QWidget | None = None
        self._drag_start_pos: int | None = None
        self._drag_start_span: int = 0
        self._hover: bool = False
        self._slide_widget: QWidget | None = None

        if self._expand_direction in ("left", "right"):
            self.setFixedWidth(_HANDLE_WIDTH)
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            self.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Expanding,
            )
        else:
            self.setFixedHeight(_HANDLE_WIDTH)
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
        self.setMouseTracking(True)

    def attach_content(self, content: QWidget) -> None:
        """Register the content widget whose width this handle controls."""
        self._content = content

    def attach_slide(self, slide: QWidget) -> None:
        """Register the slide container to keep in sync when handle is dragged."""
        self._slide_widget = slide

    # ── mouse ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._content:
            global_pos = event.globalPosition().toPoint()
            if self._expand_direction in ("left", "right"):
                self._drag_start_pos = global_pos.x()
                self._drag_start_span = self._content.width()
            else:
                self._drag_start_pos = global_pos.y()
                self._drag_start_span = self._content.height()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_pos is None or self._content is None:
            return
        global_pos = event.globalPosition().toPoint()
        if self._expand_direction in ("left", "right"):
            delta = global_pos.x() - self._drag_start_pos
            if self._expand_direction == "left":
                # Handle on right/inner side of content → drag right widens
                span = self._drag_start_span + delta
            else:
                # Handle on left/inner side of content → drag left widens
                span = self._drag_start_span - delta
            span = max(_MIN_CONTENT_WIDTH, min(_MAX_CONTENT_WIDTH, span))
            self._content.setFixedWidth(int(span))
            if self._slide_widget is not None:
                self._slide_widget.setFixedWidth(int(span) + _HANDLE_WIDTH)
        else:
            delta = global_pos.y() - self._drag_start_pos
            span = self._drag_start_span - delta
            span = max(_MIN_CONTENT_HEIGHT, min(_MAX_CONTENT_HEIGHT, span))
            self._content.setFixedHeight(int(span))
            if self._slide_widget is not None:
                self._slide_widget.setFixedHeight(int(span) + _HANDLE_WIDTH)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start_pos = None
        self.update()

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self.update()

    # ── paint ──────────────────────────────────────────────────────────

    def paintEvent(self, event: object) -> None:
        p = QPainter(self)
        w, h = self.width(), self.height()

        if self._drag_start_pos is not None:
            p.fillRect(0, 0, w, h, QColor(_HANDLE_DRAG))
        elif self._hover:
            p.fillRect(0, 0, w, h, QColor(_HANDLE_HOVER))
        else:
            p.fillRect(0, 0, w, h, QColor(_HANDLE_IDLE))
        p.end()


# ── _PanelRibbon (permanent vertical ribbon, always visible) ──────────────────


class _PanelRibbon(QWidget):
    """Permanent vertical ribbon strip shown at all times.

    Layout (top → bottom):
    * Arrow zone  — ``_ARROW_ZONE`` px tall, arrow centred within it.
      *Collapsed*: arrow points toward content (into expand direction).
      *Expanded*:  arrow points away from content (toward ribbon side).
    * Optional icon — ``_ICON_SIZE`` px square, centred horizontally.
    * Rotated title text — fills remaining height, always rotated 90° CW
      (reads top → bottom), regardless of ``expand_direction``.
    """

    clicked: Signal = Signal()

    def __init__(
        self,
        title: str,
        expand_direction: str,
        expanded: bool,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._expand_direction = expand_direction
        self._expanded = expanded
        self._icon: QIcon | None = icon
        self._text_color: QColor = QColor(_TEXT_COLOR)
        self._hover: bool = False
        self._pressed: bool = False

        self.setFixedWidth(_STRIP_WIDTH)
        self.setToolTip(title)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Expanding)

    # ── public setters ────────────────────────────────────────────────

    def set_expanded(self, expanded: bool) -> None:
        """Update arrow direction (does not show/hide anything here)."""
        self._expanded = expanded
        self.update()

    def set_icon(self, icon: QIcon | None) -> None:
        """Update the optional icon."""
        self._icon = icon
        self.update()

    def set_title(self, title: str) -> None:
        """Update the title text and tooltip."""
        self._title = title
        self.setToolTip(title)
        self.update()

    def text_color(self) -> QColor:
        """Return the current title text color."""
        return QColor(self._text_color)

    def set_text_color(self, color: QColor | str) -> None:
        """Update title text color without changing the ribbon background."""
        self._text_color = QColor(color)
        self.update()

    def reset_text_color(self) -> None:
        """Restore the default title text color."""
        self.set_text_color(_TEXT_COLOR)

    # ── mouse events ─────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._pressed = True
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self._pressed = False
        self.update()

    # ── painting ─────────────────────────────────────────────────────

    def paintEvent(self, event: object) -> None:  # noqa: C901
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2.0

        # ── Background ───────────────────────────────────────────────
        if self._pressed:
            bg = QColor(_BG_PRESSED)
        elif self._hover:
            bg = QColor(_BG_HOVER)
        else:
            bg = QColor(_BG_NORMAL)
        p.fillRect(0, 0, w, h, bg)

        # ── Border on content side ───────────────────────────────────
        p.setPen(QPen(QColor(_BORDER_COLOR), 1))
        if self._expand_direction == "right":
            p.drawLine(w - 1, 0, w - 1, h)
        else:
            p.drawLine(0, 0, 0, h)

        # ── Arrow ────────────────────────────────────────────────────
        # Collapsed → arrow points toward content (expand direction).
        # Expanded  → arrow points away from content (collapse direction).
        # expand_direction="right": collapsed=▸ right, expanded=◂ left
        # expand_direction="left":  collapsed=◂ left,  expanded=▸ right
        arrow_cy = _ARROW_ZONE / 2.0
        half = _ARROW_SIZE / 2.0

        point_right = (self._expand_direction == "right") != self._expanded

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_ARROW_COLOR))

        if point_right:
            pts = [
                QPointF(cx - half * 0.5, arrow_cy - half),
                QPointF(cx - half * 0.5, arrow_cy + half),
                QPointF(cx + half * 0.5, arrow_cy),
            ]
        else:
            pts = [
                QPointF(cx + half * 0.5, arrow_cy - half),
                QPointF(cx + half * 0.5, arrow_cy + half),
                QPointF(cx - half * 0.5, arrow_cy),
            ]
        p.drawPolygon(QPolygonF(pts))

        # ── Optional icon below arrow zone ───────────────────────────
        next_y: float = _ARROW_ZONE + 4
        if self._icon and not self._icon.isNull():
            icon_x = int(cx - _ICON_SIZE / 2)
            self._icon.paint(
                p,
                QRect(icon_x, int(next_y), _ICON_SIZE, _ICON_SIZE),
            )
            next_y += _ICON_SIZE + 4

        # ── Rotated title text (always 90° CW — reads top → bottom) ──
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        fm = p.fontMetrics()
        p.setPen(QPen(self._text_color, 1))

        available = h - next_y - _TEXT_PADDING
        if available >= fm.height():
            title = fm.elidedText(
                self._title, Qt.TextElideMode.ElideRight, int(available))

            # Rotate 90° CW: after rotate(90) the new X-axis runs downward.
            # To centre the text baseline in the strip width:
            # tx = (w - fm.ascent() + fm.descent()) / 2
            tx = (w - fm.ascent() + fm.descent()) / 2.0
            p.save()
            p.translate(tx, next_y + _TEXT_PADDING)
            p.rotate(90)
            p.drawText(0, 0, title)
            p.restore()

        p.end()


class _PanelRibbonHorizontal(QWidget):
    """Permanent horizontal ribbon strip shown at all times."""

    clicked: Signal = Signal()

    def __init__(
        self,
        title: str,
        expand_direction: str,
        expanded: bool,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._expand_direction = expand_direction
        self._expanded = expanded
        self._icon: QIcon | None = icon
        self._text_color: QColor = QColor(_TEXT_COLOR)
        self._hover: bool = False
        self._pressed: bool = False

        self.setFixedHeight(_STRIP_WIDTH)
        self.setToolTip(title)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.update()

    def set_icon(self, icon: QIcon | None) -> None:
        self._icon = icon
        self.update()

    def set_title(self, title: str) -> None:
        self._title = title
        self.setToolTip(title)
        self.update()

    def text_color(self) -> QColor:
        """Return the current title text color."""
        return QColor(self._text_color)

    def set_text_color(self, color: QColor | str) -> None:
        """Update title text color without changing the ribbon background."""
        self._text_color = QColor(color)
        self.update()

    def reset_text_color(self) -> None:
        """Restore the default title text color."""
        self.set_text_color(_TEXT_COLOR)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._pressed = True
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def enterEvent(self, event: object) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hover = False
        self._pressed = False
        self.update()

    def paintEvent(self, event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._pressed:
            bg = QColor(_BG_PRESSED)
        elif self._hover:
            bg = QColor(_BG_HOVER)
        else:
            bg = QColor(_BG_NORMAL)
        p.fillRect(0, 0, w, h, bg)

        p.setPen(QPen(QColor(_BORDER_COLOR), 1))
        if self._expand_direction == "bottom":
            p.drawLine(0, h - 1, w, h - 1)
        else:
            p.drawLine(0, 0, w, 0)

        ax = 7
        cy = h / 2.0
        half = _ARROW_SIZE / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_ARROW_COLOR))

        point_down = (self._expand_direction == "bottom") != self._expanded
        if point_down:
            pts = [
                QPointF(ax - half * 0.35, cy - half * 0.4),
                QPointF(ax + half * 0.35, cy - half * 0.4),
                QPointF(ax, cy + half * 0.6),
            ]
        else:
            pts = [
                QPointF(ax - half * 0.35, cy + half * 0.4),
                QPointF(ax + half * 0.35, cy + half * 0.4),
                QPointF(ax, cy - half * 0.6),
            ]
        p.drawPolygon(QPolygonF(pts))

        text_x = 18
        if self._icon and not self._icon.isNull():
            self._icon.paint(p, QRect(text_x, int(
                cy - _ICON_SIZE / 2), _ICON_SIZE, _ICON_SIZE))
            text_x += _ICON_SIZE + 4

        p.setPen(QPen(self._text_color, 1))
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        fm = p.fontMetrics()
        text_y = (h + fm.ascent() - fm.descent()) / 2.0
        p.drawText(int(text_x), int(text_y), fm.elidedText(
            self._title, Qt.TextElideMode.ElideRight, max(10, w - text_x - 8)))
        p.end()


# ── QCollapsiblePanel ─────────────────────────────────────────────────────────


class QCollapsiblePanel(QWidget):
    """A panel with a permanent ribbon that collapses its content area.

    The ribbon strip is *always* visible.  Clicking the ribbon shows or hides
    the content area beside it.  The ribbon appearance stays constant — only
    the arrow direction changes to indicate the available action.

    When expanded, a thin drag handle appears on the outer edge of the content
    area.  Drag to resize the active span (width for left/right, height for
    top/bottom). The expanded span is included in persistence state.

    Args:
        parent: Parent widget.
        title: Panel title shown as rotated text in the ribbon and as a tooltip.
        expand_direction: One of ``"right"``, ``"left"``, ``"top"``,
            ``"bottom"``.
        initially_expanded: Whether the panel starts with content visible.
        strip_width: Ribbon thickness in pixels.
        content_width: Initial content area width in pixels when expanded.
        content_height: Initial content area height for top/bottom panels.
        icon: Optional ``QIcon`` shown between the arrow zone and the text.
        animated: Whether to animate collapse/expand transitions.
            When False, content appears/disappears instantly. Default True.

    Signals:
        toggled(bool): Emitted when the panel expands or collapses.

    Example::

        panel = QCollapsiblePanel(
            title="File Browser", expand_direction="right")
        panel.content_layout.addWidget(my_file_browser_widget)
        panel.toggled.connect(lambda exp: print("expanded" if exp else "collapsed"))
    """

    toggled: Signal = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "Panel",
        expand_direction: str = "right",
        initially_expanded: bool = True,
        strip_width: int = _STRIP_WIDTH,
        content_width: int = _DEFAULT_CONTENT_WIDTH,
        content_height: int = _DEFAULT_CONTENT_HEIGHT,
        icon: QIcon | None = None,
        animated: bool = True,
    ) -> None:
        super().__init__(parent)
        if expand_direction not in ("left", "right", "top", "bottom"):
            raise ValueError(
                "expand_direction must be 'left', 'right', 'top', or 'bottom', "
                f"got {expand_direction!r}"
            )

        self._expanded = initially_expanded
        self._title = title
        self._expand_direction = expand_direction
        self._strip_width = strip_width
        self._content_width = content_width
        self._content_height = content_height
        self._icon: QIcon | None = icon
        self._animated = animated

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _is_horizontal_layout(self) -> bool:
        return self._expand_direction in ("left", "right")

    def _content_span(self) -> int:
        if self._is_horizontal_layout():
            return self._content_width
        return self._content_height

    def _set_content_span(self, span: int) -> None:
        if self._is_horizontal_layout():
            clamped = max(_MIN_CONTENT_WIDTH, min(
                _MAX_CONTENT_WIDTH, int(span)))
            self._content_width = clamped
            self._content.setFixedWidth(clamped)
            self._slide.setFixedWidth(clamped + _HANDLE_WIDTH)
        else:
            clamped = max(_MIN_CONTENT_HEIGHT, min(
                _MAX_CONTENT_HEIGHT, int(span)))
            self._content_height = clamped
            self._content.setFixedHeight(clamped)
            self._slide.setFixedHeight(clamped + _HANDLE_WIDTH)

    def _build_ui(self) -> None:
        if self._is_horizontal_layout():
            root: QHBoxLayout | QVBoxLayout = QHBoxLayout(self)
        else:
            root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if self._is_horizontal_layout():
            self._ribbon = _PanelRibbon(
                self._title,
                self._expand_direction,
                self._expanded,
                icon=self._icon,
                parent=self,
            )
            self._ribbon.setFixedWidth(self._strip_width)
        else:
            self._ribbon = _PanelRibbonHorizontal(
                self._title,
                self._expand_direction,
                self._expanded,
                icon=self._icon,
                parent=self,
            )
            self._ribbon.setFixedHeight(self._strip_width)
        self._ribbon.clicked.connect(self._toggle)

        # Content container and resize handle are wrapped in a slide widget.
        # Animating the slide keeps the ribbon outside the animated subtree,
        # preventing it from jittering during open/close transitions.
        self._slide = QWidget()
        self._slide.setMinimumWidth(0)
        self._slide.setMinimumHeight(0)
        if self._is_horizontal_layout():
            slide_inner: QHBoxLayout | QVBoxLayout = QHBoxLayout(self._slide)
        else:
            slide_inner = QVBoxLayout(self._slide)
        slide_inner.setContentsMargins(0, 0, 0, 0)
        slide_inner.setSpacing(0)

        self._content = QWidget()
        if self._is_horizontal_layout():
            self._content.setFixedWidth(self._content_width)
        else:
            self._content.setFixedHeight(self._content_height)
        self.content_layout = QVBoxLayout(self._content)
        self.content_layout.setContentsMargins(6, 4, 6, 4)

        # Resize handle — on the outer edge (facing the central viewport)
        self._handle = _ResizeHandle(self._expand_direction, parent=self)
        self._handle.attach_content(self._content)
        self._handle.attach_slide(self._slide)

        if self._expand_direction == "right":
            # Content on right (outward), handle on inner/middle side.
            slide_inner.addWidget(self._handle)
            slide_inner.addWidget(self._content)
            root.addWidget(self._ribbon)
            root.addWidget(self._slide)
        elif self._expand_direction == "left":
            # Content on left (outward), handle on inner/middle side.
            slide_inner.addWidget(self._content)
            slide_inner.addWidget(self._handle)
            root.addWidget(self._slide)
            root.addWidget(self._ribbon)
        elif self._expand_direction == "top":
            slide_inner.addWidget(self._content)
            slide_inner.addWidget(self._handle)
            root.addWidget(self._slide)
            root.addWidget(self._ribbon)
        else:
            slide_inner.addWidget(self._handle)
            slide_inner.addWidget(self._content)
            root.addWidget(self._ribbon)
            root.addWidget(self._slide)

        if self._is_horizontal_layout():
            self._slide.setFixedWidth(self._content_width + _HANDLE_WIDTH)
        else:
            self._slide.setFixedHeight(self._content_height + _HANDLE_WIDTH)
        self._slide.setVisible(self._expanded)
        self._anim: QVariantAnimation | None = None

    # ------------------------------------------------------------------
    # Toggle
    # ------------------------------------------------------------------

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._ribbon.set_expanded(self._expanded)
        # Snapshot span before collapsing so we can restore on expand.
        if not self._expanded:
            if self._is_horizontal_layout():
                self._content_width = self._content.width()
            else:
                self._content_height = self._content.height()
        self._animate_panel(self._expanded)
        self.toggled.emit(self._expanded)

    def _animate_panel(self, expanding: bool) -> None:
        """Slide the content pane open or shut along the active layout axis."""
        if self._anim is not None:
            self._anim.stop()

        full_slide = self._content_span() + _HANDLE_WIDTH

        if expanding:
            if self._is_horizontal_layout():
                self._slide.setFixedWidth(0)
            else:
                self._slide.setFixedHeight(0)
            self._slide.setVisible(True)
            start, end = 0, full_slide
        else:
            if self._is_horizontal_layout():
                start, end = self._slide.width(), 0
            else:
                start, end = self._slide.height(), 0

        if not self._animated:
            # Instant toggle — apply end state directly
            if expanding:
                if self._is_horizontal_layout():
                    self._slide.setFixedWidth(end)
                else:
                    self._slide.setFixedHeight(end)
            else:
                self._slide.setVisible(False)
                if self._is_horizontal_layout():
                    self._slide.setFixedWidth(full_slide)
                else:
                    self._slide.setFixedHeight(full_slide)
            return

        anim = QVariantAnimation(self)
        anim.setDuration(_PANEL_ANIM_MS)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if self._is_horizontal_layout():
            anim.valueChanged.connect(
                lambda v: self._slide.setFixedWidth(int(v)))
        else:
            anim.valueChanged.connect(
                lambda v: self._slide.setFixedHeight(int(v)))

        if not expanding:
            def _on_collapse_done() -> None:
                self._slide.setVisible(False)
                if self._is_horizontal_layout():
                    self._slide.setFixedWidth(full_slide)
                else:
                    self._slide.setFixedHeight(full_slide)
            anim.finished.connect(_on_collapse_done)

        self._anim = anim
        anim.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def expand(self) -> None:
        """Expand the panel to show its content."""
        if not self._expanded:
            self._toggle()

    def collapse(self) -> None:
        """Collapse the panel to the ribbon only."""
        if self._expanded:
            self._toggle()

    @property
    def is_expanded(self) -> bool:
        """Whether the panel content is currently visible."""
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        """Programmatically set expanded state."""
        if expanded != self._expanded:
            self._toggle()

    def set_title(self, title: str) -> None:
        """Update the panel title."""
        self._title = title
        self._ribbon.set_title(title)

    def set_icon(self, icon: QIcon | None) -> None:
        """Update the optional icon shown in the ribbon."""
        self._icon = icon
        self._ribbon.set_icon(icon)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize panel state (expanded flag + active span)."""
        span = self._content.width() if self._is_horizontal_layout() else self._content.height()
        if not self._expanded:
            span = self._content_span()
        state: dict[str, Any] = {"expanded": self._expanded}
        if self._is_horizontal_layout():
            state["content_width"] = span
        else:
            state["content_height"] = span
        return state

    def from_dict(self, state: dict[str, Any]) -> None:
        """Restore panel state."""
        if "content_height" in state:
            h = max(_MIN_CONTENT_HEIGHT, min(
                _MAX_CONTENT_HEIGHT, int(state["content_height"])))
            self._content_height = h
            if not self._is_horizontal_layout():
                self._set_content_span(h)
        if "content_width" in state:
            w = max(_MIN_CONTENT_WIDTH,
                    min(_MAX_CONTENT_WIDTH, int(state["content_width"])))
            self._content_width = w
            if self._is_horizontal_layout():
                self._set_content_span(w)
        if "expanded" in state:
            self.set_expanded(bool(state["expanded"]))


__all__ = ["QCollapsiblePanel"]
