"""Fixed-size square icon-only button for PySide6 UIs."""
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

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider


class QSquareIconButton(QPushButton):
    """Icon-only button that always stays square and never stretches.

    Defaults are intentionally minimal for overlay/icon use-cases:
    - transparent background
    - no border
    - zero padding
    - icon fills the square button area
    """

    def __init__(
        self,
        edge: int,
        *,
        icon: QIcon | None = None,
        tooltip: str = "",
        show_border: bool = False,
        show_backdrop: bool = False,
        border_color: str | None = None,
        backdrop_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._edge = max(1, int(edge))
        self._show_border = bool(show_border)
        self._show_backdrop = bool(show_backdrop)
        if border_color is None:
            provider = QThemeProvider.instance()
            border_color = provider.color("border").name(QColor.NameFormat.HexArgb)
        if backdrop_color is None:
            provider = QThemeProvider.instance()
            backdrop_color = provider.color("overlay_bg").name(QColor.NameFormat.HexArgb)
        self._border_color = border_color
        self._backdrop_color = backdrop_color
        self.setFlat(True)
        self.setObjectName("square_icon_button")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(self._edge, self._edge)
        self.setMaximumSize(self._edge, self._edge)
        self.setFixedSize(self._edge, self._edge)
        self._apply_style()
        if tooltip:
            self.setToolTip(tooltip)
        if icon is not None:
            self.set_square_icon(icon)

    def _apply_style(self) -> None:
        border = f"1px solid {self._border_color}" if self._show_border else "0"
        base_bg = self._backdrop_color if self._show_backdrop else "transparent"
        hover_bg = self._backdrop_color if self._show_backdrop else "transparent"
        self.setStyleSheet(
            "QPushButton {"
            f"background: {base_bg};"
            f"border: {border};"
            "padding: 0;"
            "margin: 0;"
            f"min-width: {self._edge}px;"
            f"max-width: {self._edge}px;"
            f"min-height: {self._edge}px;"
            f"max-height: {self._edge}px;"
            "}"
            "QPushButton:pressed {"
            f"background: {base_bg};"
            f"border: {border};"
            "}"
            "QPushButton:hover {"
            f"background: {hover_bg};"
            f"border: {border};"
            "}"
        )

    def set_square_icon(self, icon: QIcon) -> None:
        """Set icon and keep it sized exactly to the button edge."""
        self.setIcon(icon)
        self.setIconSize(QSize(self._edge, self._edge))

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(self._edge, self._edge)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(self._edge, self._edge)


__all__ = ["QSquareIconButton"]
