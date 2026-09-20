"""
Dark theme stylesheet for PySide6 GUIs.

Provides a consistent dark theme matching ttkbootstrap "darkly" for
visual parity with existing tkinter GUIs.
"""

from __future__ import annotations
import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(
            None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass


from PySide6.QtWidgets import QApplication

from ported.lks_utils.gui_qt.theme.colors import COLORS

# =============================================================================
# Extend format dict with branch-indicator SVG data URIs for QTreeView::branch
# =============================================================================
DARK_QSS = """
QWidget {
    background-color: %(bg)s;
    color: %(fg)s;
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}

QPushButton {
    background-color: %(primary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 6px 16px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: %(primary_hover)s;
}

QPushButton:pressed {
    background-color: %(primary_pressed)s;
}

QPushButton:disabled {
    background-color: %(secondary)s;
    color: %(disabled_fg)s;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: %(input_bg)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 4px 8px;
    padding-right: 26px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid %(primary)s;
}

QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background-color: %(secondary)s;
    color: %(disabled_fg)s;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid %(border)s;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: %(secondary)s;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: %(input_bg)s;
    color: %(fg)s;
    selection-background-color: %(primary)s;
    selection-color: %(fg)s;
    border: 1px solid %(border)s;
}

/* Some styles can host combo popups in a top-level view/frame rather than
   a child selector target. Force opaque list/dropdown popups globally. */
QAbstractItemView {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(border)s;
    selection-background-color: %(primary)s;
    selection-color: %(fg)s;
}

QListView {
    background-color: %(input_bg)s;
    color: %(fg)s;
    border: 1px solid %(border)s;
}

QSpinBox, QDoubleSpinBox {
    background-color: %(input_bg)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 4px 8px;
    color: %(fg)s;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid %(primary)s;
}

QProgressBar {
    background-color: %(secondary)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: %(success)s;
    border-radius: 3px;
}

QGroupBox {
    border: 1px solid %(border)s;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QTabWidget::pane {
    border: 1px solid %(border)s;
    border-radius: 4px;
    background-color: %(bg)s;
}

QTabBar::tab {
    background-color: %(secondary)s;
    border: 1px solid %(border)s;
    padding: 8px 16px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: %(primary)s;
}

QTabBar::tab:hover {
    background-color: %(primary_hover)s;
}

QScrollBar:vertical {
    background: %(scrollbar_bg)s;
    width: 12px;
    border: none;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: %(scrollbar_handle)s;
    border-radius: 6px;
    min-height: 20px;
    margin: 0px;
}

QScrollBar::handle:vertical:hover {
    background: %(scrollbar_handle_hover)s;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: %(scrollbar_bg)s;
}

QScrollBar:horizontal {
    background: %(scrollbar_bg)s;
    height: 12px;
    border: none;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: %(scrollbar_handle)s;
    border-radius: 6px;
    min-width: 20px;
    margin: 0px;
}

QScrollBar::handle:horizontal:hover {
    background: %(scrollbar_handle_hover)s;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: %(scrollbar_bg)s;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid %(border)s;
    border-radius: 3px;
    background-color: %(input_bg)s;
}

QCheckBox::indicator:checked {
    background-color: %(primary)s;
    border-color: %(primary)s;
}

QCheckBox::indicator:hover {
    border-color: %(primary)s;
}

QRadioButton {
    spacing: 8px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid %(border)s;
    border-radius: 8px;
    background-color: %(input_bg)s;
}

QRadioButton::indicator:checked {
    background-color: %(primary)s;
    border-color: %(primary)s;
}

QRadioButton::indicator:hover {
    border-color: %(primary)s;
}

QLabel {
    background-color: transparent;
}

QFrame {
    background-color: transparent;
}

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    background-color: %(border)s;
    max-height: 1px;
}

QTableWidget, QTreeWidget, QTreeView {
    background-color: %(input_bg)s;
    alternate-background-color: %(secondary)s;
    color: %(fg)s;
    border: 1px solid %(border)s;
    gridline-color: %(border)s;
    selection-background-color: %(primary)s;
    selection-color: %(fg)s;
}

QTableWidget::item {
    color: %(fg)s;
    padding: 6px 4px;  /* Increased vertical padding from 4px to 6px to prevent text clipping */
}
/* Tree items inherit colour from the widget's palette (set via darken_treeview)
   so that per-item setForeground() colour overrides work correctly. */
QTreeWidget::item, QTreeView::item {
    padding: 6px 4px;
}

/* Keep colour on alternate/selected so they match table-item behaviour */
QTableWidget::item:alternate {
    background-color: %(secondary)s;
    color: %(fg)s;
}
QTreeWidget::item:alternate, QTreeView::item:alternate {
    background-color: %(secondary)s;
}

QTableWidget::item:selected {
    background-color: %(primary)s;
    color: %(fg)s;
}
QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: %(primary)s;
}

QTreeView {
    show-decoration-selected: 1;
    color: %(fg)s;
    background-color: %(tree_alt_bg)s;
    outline: none;
}
/* Force light branch indicators: Qt draws OS-native arrows following
   QPalette::Text. Explicit QTreeView::item color alone doesn't propagate
   to the branch arrow glyph -- setting color on QTreeView itself does. */
QTreeView::branch {
    background-color: %(tree_alt_bg)s;
}
QTreeView::branch:has-siblings:!adjoins-item {
    background-color: %(tree_alt_bg)s;
}
QTreeView::branch:has-siblings:adjoins-item {
    background-color: %(tree_alt_bg)s;
}
QTreeView::branch:!has-children:!has-siblings:adjoins-item {
    background-color: %(tree_alt_bg)s;
}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    background-color: %(tree_alt_bg)s;
}
QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {
    background-color: %(tree_alt_bg)s;
}

QHeaderView::section {
    background-color: %(secondary)s;
    color: %(fg)s;
    border: 1px solid %(border)s;
    padding: 4px 8px;
}

QMenu {
    background-color: %(bg)s;
    border: 1px solid %(border)s;
}

QMenu::item {
    padding: 4px 24px 4px 8px;
}

QMenu::item:selected {
    background-color: %(primary)s;
}

QToolTip {
    background-color: %(dark)s;
    border: 1px solid %(border)s;
    color: %(fg)s;
    padding: 4px;
}

QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
""" % COLORS


_DARK_THEME_SENTINEL = "_lks_dark_theme_applied"


def apply_dark_theme(app: QApplication) -> None:
    """
    Apply dark theme stylesheet to the application.

    Idempotent: subsequent calls on the same QApplication instance are no-ported.ops,
    preventing repeated setStyleSheet() calls that can crash Qt on Windows when
    called many times across a test session.

    Args:
        app: QApplication instance to style

    Example:
        >>> app = QApplication(sys.argv)
        >>> apply_dark_theme(app)
        >>> window = MyMainWindow()
        >>> window.show()
        >>> sys.exit(app.exec())
    """
    if getattr(app, _DARK_THEME_SENTINEL, False):
        return
    setattr(app, _DARK_THEME_SENTINEL, True)
    app.setStyleSheet(DARK_QSS)


def darken_treeview(tree: "QTreeView | QTreeWidget", branch_scale: float = 1.0) -> None:
    """Force light branch-indicator arrows on a dark-themed QTreeView.

    Uses a ``QProxyStyle`` that *replaces* ``PE_IndicatorBranch`` drawing
    for nodes with children, painting bright triangle arrows directly.

    IMPORTANT: Do NOT call ``setStyleSheet()`` on this tree — QSS wraps
    the style in ``QStyleSheetStyle``, which intercepts ``drawPrimitive``
    before the proxy sees it.

    Args:
        tree: The QTreeView or QTreeWidget to style.
        branch_scale: Scale factor for branch arrow size (1.0 = default,
            0.5 = half size).
    """
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import (
        QColor, QPalette, QPen, QBrush, QPainter, QPainterPath,
    )
    from PySide6.QtWidgets import QStyle, QStyleOption, QProxyStyle

    _BG = QColor("#252525")
    _FG = QColor("#cccccc")

    r: float = 6.0 * branch_scale
    pen_width: float = max(1.0, 2.0 * branch_scale)

    class _LightBranchStyle(QProxyStyle):
        """Replace branch arrow drawing with visible light-coloured triangles."""

        def drawPrimitive(
            self,
            element: QStyle.PrimitiveElement,
            option: QStyleOption,
            painter: "QPainter",
            widget: "QWidget | None" = None,
        ) -> None:
            if (
                element == QStyle.PrimitiveElement.PE_IndicatorBranch
                and (option.state & QStyle.StateFlag.State_Children)
            ):
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                rect = QRectF(option.rect)
                cx = rect.center().x()
                cy = rect.center().y()

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(_BG))
                painter.drawRect(rect)

                painter.setPen(QPen(_FG, pen_width))
                painter.setBrush(_FG)

                if option.state & QStyle.StateFlag.State_Open:
                    # ▼
                    path = QPainterPath()
                    path.moveTo(cx - r, cy - r * 0.4)
                    path.lineTo(cx, cy + r * 0.6)
                    path.lineTo(cx + r, cy - r * 0.4)
                    path.closeSubpath()
                else:
                    # ▶
                    path = QPainterPath()
                    path.moveTo(cx - r * 0.4, cy - r)
                    path.lineTo(cx + r * 0.6, cy)
                    path.lineTo(cx - r * 0.4, cy + r)
                    path.closeSubpath()

                painter.drawPath(path)
                painter.restore()
            else:
                super().drawPrimitive(element, option, painter, widget)

    tree.setStyleSheet("")
    tree.setStyle(_LightBranchStyle(tree.style()))

    pal: QPalette = tree.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor("#252525"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#2d2d2d"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#dddddd"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#dddddd"))
    tree.setPalette(pal)


__all__ = ["DARK_QSS", "apply_dark_theme", "darken_treeview"]
