"""Single option row (adornments + elided label) for QDialEnumPicker."""
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

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from ported.lks_utils.gui_qt.widgets.dial_enum_option import DialEnumOption
from ported.lks_utils.gui_qt.widgets.dial_enum_picker_metrics import (
    ADORNMENT_GAP_PX,
    ADORNMENT_SIZE_PX,
    DEFAULT_ROW_HEIGHT_PX,
)
from ported.lks_utils.gui_qt.widgets.elided_label import QElidedLabel


class _DialEnumOptionRowWidget(QWidget):
    """Horizontal row showing one DialEnumOption."""

    clicked = Signal()

    def __init__(
        self,
        option: DialEnumOption,
        *,
        adornment_px: int = ADORNMENT_SIZE_PX,
        display_only: bool = False,
        selectable: bool = False,
        text_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adornment_px = adornment_px
        self._display_only = display_only
        self._selectable = selectable
        self._text_color: str = text_color or "#f0f0f0"
        self._fill_color: str = "transparent"

        if display_only:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        if selectable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(False)

        layout = QHBoxLayout(self)
        left_pad = 8 if selectable else 0
        layout.setContentsMargins(left_pad, 0, 0, 0)
        layout.setSpacing(ADORNMENT_GAP_PX)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._leading_label = self._make_adornment_label(option.leading)
        self._text_label = QElidedLabel(option.label, self, selectable=False)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._trailing_label = self._make_adornment_label(option.trailing)

        if self._leading_label is not None:
            layout.addWidget(self._leading_label, 0)
        layout.addWidget(self._text_label, 1)
        if self._trailing_label is not None:
            layout.addWidget(self._trailing_label, 0)

        if text_color is not None:
            self.apply_text_color(text_color)

        if display_only:
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
        else:
            self.setFixedHeight(DEFAULT_ROW_HEIGHT_PX)

    def apply_row_fill(self, fill_color: str) -> None:
        """Set popup row background (selection / hover)."""
        self._fill_color = fill_color
        self._apply_row_style()

    def apply_text_color(self, color: str) -> None:
        """Set label text colour; adornment hosts stay untouched."""
        self._text_color = color
        self._apply_row_style()

    def _apply_row_style(self) -> None:
        self.setStyleSheet(f"background-color: {self._fill_color};")
        self._text_label.setStyleSheet(
            f"color: {self._text_color}; background: transparent;"
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if (
            self._selectable
            and event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(event.position().toPoint())
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def set_option(self, option: DialEnumOption) -> None:
        """Update row contents."""
        self._apply_adornment(self._leading_label, option.leading)
        self._text_label.setText(option.label)
        self._apply_adornment(self._trailing_label, option.trailing)

    def full_label(self) -> str:
        """Return the unelided option label."""
        return self._text_label.text()

    def _make_adornment_label(
        self, adornment: QIcon | QWidget | None
    ) -> QLabel | None:
        if adornment is None:
            return None
        label = QLabel(self)
        label.setFixedSize(self._adornment_px, self._adornment_px)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        label.setStyleSheet("background: transparent;")
        self._apply_adornment(label, adornment)
        return label

    def _apply_adornment(
        self, label: QLabel | None, adornment: QIcon | QWidget | None
    ) -> None:
        if label is None:
            return
        if adornment is None:
            label.clear()
            label.hide()
            return
        label.show()
        if isinstance(adornment, QIcon):
            pixmap = adornment.pixmap(
                QSize(self._adornment_px, self._adornment_px),
                QIcon.Mode.Normal,
                QIcon.State.Off,
            )
            label.setPixmap(pixmap)
            return
        pixmap = adornment.grab()
        if pixmap.isNull():
            label.clear()
            return
        scaled = pixmap.scaled(
            self._adornment_px,
            self._adornment_px,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)

    def sizeHint(self) -> QSize:  # noqa: N802 — Qt API name
        base = super().sizeHint()
        if self._display_only:
            return base
        return QSize(base.width(), DEFAULT_ROW_HEIGHT_PX)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 — Qt API name
        if self._display_only:
            return super().minimumSizeHint()
        return self.sizeHint()
