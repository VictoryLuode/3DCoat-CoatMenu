"""SectionHeader widget - A styled section header label.

Provides consistent styling for section headers in Qt panels.
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

from PySide6.QtWidgets import QLabel, QWidget

# Default colors for headers
DEFAULT_HEADER_COLOR: str = "#ffb74d"  # Orange
DEFAULT_SUBHEADER_COLOR: str = "#90caf9"  # Blue


class QSectionHeader(QLabel):
    """A styled section header label.

    Args:
        parent: Parent widget
        text: Header text
        sub: If True, use smaller sub-header style
        color: Text color (hex or Qt color name)

    Example:
        header = QSectionHeader(parent, text="Main Section")
        sub_header = QSectionHeader(parent, text="Sub Section", sub=True)
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        text: str = "",
        sub: bool = False,
        color: str | None = None,
    ) -> None:
        """Initialize section header.

        Args:
            parent: Parent widget
            text: Header text
            sub: If True, use sub-header style
            color: Text color override
        """
        super().__init__(text, parent)

        # Determine styling based on header type
        font_size = "10px" if sub else "11px"

        if color is not None:
            header_color = color
        else:
            header_color = DEFAULT_SUBHEADER_COLOR if sub else DEFAULT_HEADER_COLOR

        self.setStyleSheet(
            f"""
            QLabel {{
                font-weight: bold;
                font-size: {font_size};
                color: {header_color};
                padding: 2px 0;
            }}
        """
        )

    def set_color(self, color: str) -> None:
        """Update the header color.

        Args:
            color: New color (hex or Qt color name)
        """
        # Preserve current font size by checking current style
        current_style = self.styleSheet()
        if "10px" in current_style:
            font_size = "10px"
        else:
            font_size = "11px"

        self.setStyleSheet(
            f"""
            QLabel {{
                font-weight: bold;
                font-size: {font_size};
                color: {color};
                padding: 2px 0;
            }}
        """
        )
