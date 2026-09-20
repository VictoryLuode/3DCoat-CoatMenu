"""QLabel variant that elides overflowing text with an ellipsis."""
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

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel, QWidget


class QElidedLabel(QLabel):
    """A QLabel that renders text as elided when width is constrained.

    The full unelided text is preserved as the tooltip so users can inspect
    the complete value on hover.
    """

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        elide_mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight,
        selectable: bool = True,
    ) -> None:
        super().__init__(parent)
        self._full_text = text
        self._elide_mode = elide_mode
        flags = (
            Qt.TextInteractionFlag.TextSelectableByMouse
            if selectable
            else Qt.TextInteractionFlag.NoTextInteraction
        )
        self.setTextInteractionFlags(flags)
        self.setText(text)

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full_text = text
        self._refresh_elided_text()
        self.setToolTip(text)

    def text(self) -> str:  # type: ignore[override]
        return self._full_text

    def resizeEvent(self, event: object) -> None:
        self._refresh_elided_text()
        super().resizeEvent(event)

    def _refresh_elided_text(self) -> None:
        fm = QFontMetrics(self.font())
        available = max(0, self.contentsRect().width())
        if available <= 0:
            super().setText(self._full_text)
            return
        elided = fm.elidedText(self._full_text, self._elide_mode, available)
        super().setText(elided)


__all__ = ["QElidedLabel"]
