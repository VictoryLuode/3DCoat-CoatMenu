"""
Tooltip utilities for PySide6 applications.

Port of ported.lks_utils.gui.tooltip to Qt. Qt has built-in tooltip support,
so this module provides a convenience wrapper for consistency with
the tkinter API.
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


from PySide6.QtWidgets import QWidget


def add_tooltip(widget: QWidget, text: str) -> None:
    """
    Add a tooltip to a widget.

    This is a convenience wrapper around Qt's built-in setToolTip() method,
    provided for API consistency with the tkinter version.

    Args:
        widget: The widget to attach the tooltip to
        text: The tooltip text to display

    Example:
        button = QPushButton("Save")
        add_tooltip(button, "Save the current file")

        # Or directly:
        button.setToolTip("Save the current file")

    Note:
        Qt tooltips appear automatically on hover with system-default styling.
        The delay and appearance can be customized via QApplication settings
        or QSS stylesheets.
    """
    widget.setToolTip(text)


__all__ = ["add_tooltip"]
