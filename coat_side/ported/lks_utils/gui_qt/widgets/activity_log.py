"""
QActivityLog — A scrollable activity log with timestamped, colored messages.

Messages are appended with timestamps and color-coded by level.
Supports info, warn, error, debug, and success levels.
Includes copy-to-clipboard, clear, and expand/collapse buttons.
New entries start bright (1.5×) and fade to their base color over 1 second.
"""
from __future__ import annotations

import time as _time
from datetime import datetime
from typing import Callable

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# =============================================================================
# Constants
# =============================================================================

# Log level colors (base hex values)
LOG_COLORS: dict[str, str] = {
    "info": "#81c784",  # Green
    "warn": "#ffb74d",  # Orange
    "error": "#ef5350",  # Red
    "debug": "#90caf9",  # Blue
    "success": "#4caf50",  # Bright green
}

# Log level prefixes
LOG_PREFIXES: dict[str, str] = {
    "info": "",
    "warn": "\u26a0 ",
    "error": "\u2717 ",
    "debug": "[debug] ",
    "success": "\u2713 ",
}

# Default text edit styling
DEFAULT_LOG_STYLE: str = """
    QTextEdit {
        background: #1e1e1e;
        color: #d4d4d4;
        border: 1px solid #333;
        border-radius: 3px;
        font-family: Consolas, monospace;
        font-size: 9pt;
        padding: 4px;
        selection-background-color: #264f78;
        selection-color: #ffffff;
    }
"""

# Header bar button style
HEADER_BUTTON_STYLE: str = """
    QPushButton {
        background: #2b2b2b;
        color: #aaa;
        border: 1px solid #3a3a3a;
        border-radius: 2px;
        padding: 2px 8px;
        font-size: 8pt;
    }
    QPushButton:hover {
        background: #3a3a3a;
        color: #90caf9;
    }
"""

# Status label style
STATUS_LABEL_STYLE: str = """
    QLabel {
        color: #666;
        font-size: 8pt;
    }
"""

# Character limit before trimming
DEFAULT_MAX_CHARS: int = 200000

# Fade animation settings
FADE_DURATION_S: float = 1.0  # Seconds to fade from bright → base
FADE_BRIGHTNESS: float = 1.5  # Initial brightness multiplier
FADE_TICK_MS: int = 16  # Timer interval (~60 fps)

# Timestamp color
COLOR_TIMESTAMP: str = "#666666"


# =============================================================================
# Color math helpers
# =============================================================================


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse hex color to (r, g, b) tuple."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) to #rrggbb hex string."""
    return (
        f"#{min(255, max(0, r)):02x}"
        f"{min(255, max(0, g)):02x}"
        f"{min(255, max(0, b)):02x}"
    )


def _brighten(hex_color: str, factor: float) -> str:
    """Scale a hex color's RGB channels by factor (clamped to 255)."""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        min(255, int(r * factor)),
        min(255, int(g * factor)),
        min(255, int(b * factor)),
    )


def _lerp_color(hex_from: str, hex_to: str, t: float) -> str:
    """Linear interpolate between two hex colors. t=0 → from, t=1 → to."""
    fr, fg, fb = _hex_to_rgb(hex_from)
    tr, tg, tb = _hex_to_rgb(hex_to)
    t = max(0.0, min(1.0, t))
    return _rgb_to_hex(
        int(fr + (tr - fr) * t),
        int(fg + (tg - fg) * t),
        int(fb + (tb - fb) * t),
    )


# =============================================================================
# QActivityLog
# =============================================================================


class QActivityLog(QWidget):
    """A scrollable activity log with timestamped, colored messages.

    Messages are appended with timestamps and color-coded by level.
    Supports info, warn, error, debug, and success levels.

    Each new entry appears bright (1.5×) and fades to its base color
    over 1 second for a subtle "freshness" indicator.

    Features:
    - Copy-to-clipboard, clear, and expand/collapse buttons in header bar
    - Status label showing line and character counts
    - Character-count-based trimming (set_max_chars)
    - Selectable text for copy-paste
    - Fade-in animation on new entries

    Args:
        parent: Parent widget
        max_lines: Maximum number of lines to keep (0 = unlimited)
        show_timestamps: Whether to show timestamps
        min_height: Minimum height of the log widget
        max_height: Maximum height of the log widget
        max_chars: Maximum characters before trimming

    Example:
        log = QActivityLog(parent)
        log.log_info("Operation started")
        log.log_success("Operation complete")
        log.log_error("Something failed")
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        max_lines: int = 200,
        show_timestamps: bool = True,
        min_height: int = 100,
        max_height: int = 0,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        """Initialize activity log.

        Args:
            parent: Parent widget
            max_lines: DEPRECATED — use max_chars instead. Sets approximate char limit.
            show_timestamps: Whether to show timestamps
            min_height: Minimum height
            max_height: Maximum height (0 = no limit)
            max_chars: Maximum characters before trimming
        """
        super().__init__(parent)
        self._show_timestamps: bool = show_timestamps
        self._max_chars: int = max_chars
        if max_lines > 0 and max_lines != 200:
            # Non-default max_lines was passed — approximate to chars
            self._max_chars = max_lines * 80
        self._char_count: int = 0
        self._min_height: int = min_height
        self._max_height: int = max_height

        # Fade queue: list of dicts with start, end, base_color, insert_time
        self._fade_queue: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # --- Header Bar ---
        header = self._create_header()
        layout.addWidget(header)

        # --- Text widget ---
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(DEFAULT_LOG_STYLE)
        self._text.setMinimumHeight(min_height)
        if max_height > 0:
            self._text.setMaximumHeight(max_height)
        layout.addWidget(self._text)

        # --- Fade animation timer ---
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_tick)

    # -------------------------------------------------------------------------
    # Header Bar
    # -------------------------------------------------------------------------

    def _create_header(self) -> QWidget:
        """Create header bar with copy, expand, clear buttons, and status."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(STATUS_LABEL_STYLE)
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._copy_btn = QPushButton("\U0001f4cb Copy")
        self._copy_btn.setStyleSheet(HEADER_BUTTON_STYLE)
        self._copy_btn.setToolTip("Copy all log text to clipboard")
        self._copy_btn.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self._copy_btn)

        self._clear_btn = QPushButton("\u2715 Clear")
        self._clear_btn.setStyleSheet(HEADER_BUTTON_STYLE)
        self._clear_btn.setToolTip("Clear all log messages")
        self._clear_btn.clicked.connect(self.clear)
        layout.addWidget(self._clear_btn)

        return container

    # -------------------------------------------------------------------------
    # Logging Methods
    # -------------------------------------------------------------------------

    def _format_timestamp(self) -> str:
        """Get current timestamp string."""
        return datetime.now().strftime("%H:%M:%S")

    def _append_line(self, text: str, level: str) -> None:
        """Append a line to the log with level styling and fade animation.

        Uses QTextCursor + QTextCharFormat instead of insertHtml()
        so we can animate colors on a timer.

        Args:
            text: Message text
            level: Log level for color
        """
        base_color: str = LOG_COLORS.get(level, "#d4d4d4")
        prefix: str = LOG_PREFIXES.get(level, "")

        cursor: QTextCursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Insert timestamp in muted color (if enabled)
        ts_len: int = 0
        if self._show_timestamps:
            ts_fmt: QTextCharFormat = QTextCharFormat()
            ts_fmt.setForeground(QColor(COLOR_TIMESTAMP))
            ts_text: str = f"[{self._format_timestamp()}] "
            ts_len = len(ts_text)
            cursor.insertText(ts_text, ts_fmt)

        # Remember where the message text starts
        msg_start: int = cursor.position()

        # Build message text
        msg_text: str = f"{prefix}{text}\n"

        # Insert message with BRIGHT initial color
        bright_color: str = _brighten(base_color, FADE_BRIGHTNESS)
        msg_fmt: QTextCharFormat = QTextCharFormat()
        msg_fmt.setForeground(QColor(bright_color))
        cursor.insertText(msg_text, msg_fmt)

        # Remember where the message text ends
        msg_end: int = cursor.position()

        # Track character count and trim if needed
        self._char_count += len(msg_text) + ts_len

        # Push the document cursor back so scroll-to-end works
        self._text.setTextCursor(cursor)

        # Add to fade queue
        self._fade_queue.append({
            "start": msg_start,
            "end": msg_end,
            "base_color": base_color,
            "insert_time": _time.monotonic(),
        })

        # Start fade timer if not already running
        if not self._fade_timer.isActive():
            self._fade_timer.start(FADE_TICK_MS)

        # Trim if over limit (may shift positions)
        if self._max_chars > 0 and self._char_count > self._max_chars:
            self._trim_old_content()

        # Update status label
        self._update_status()

    def _trim_old_content(self) -> None:
        """Remove oldest content to get under the character limit.

        After trimming, adjusts all positions in the fade queue by
        subtracting the number of characters removed, and drops any
        entries whose positions were trimmed away.
        """
        target: int = self._max_chars // 2
        cursor: QTextCursor = self._text.textCursor()
        doc = self._text.document()
        old_len: int = len(doc.toPlainText())

        # Remove blocks from the start until under target
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while self._char_count > target:
            moved: bool = cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                1,
            )
            if not moved or (cursor.atEnd() and cursor.atStart()):
                break
            cursor.removeSelectedText()
            self._char_count = len(doc.toPlainText())
            cursor.movePosition(QTextCursor.MoveOperation.Start)

        # Calculate how many characters were trimmed
        new_len: int = len(doc.toPlainText())
        trimmed_count: int = old_len - new_len

        if trimmed_count <= 0:
            return

        # Adjust fade queue positions (shift everything down)
        remaining: list[dict] = []
        for entry in self._fade_queue:
            adj_start: int = entry["start"] - trimmed_count
            adj_end: int = entry["end"] - trimmed_count
            # Drop entries that were fully trimmed away
            if adj_end <= 0:
                continue
            # Clamp entries that were partially trimmed
            entry["start"] = max(0, adj_start)
            entry["end"] = adj_end
            remaining.append(entry)
        self._fade_queue = remaining

        self._char_count = new_len

    # -------------------------------------------------------------------------
    # Fade Animation
    # -------------------------------------------------------------------------

    def _fade_tick(self) -> None:
        """Called by the fade timer at ~60 fps.

        Iterates the fade queue and adjusts each entry's color from
        bright → base over FADE_DURATION_S seconds.
        Stops the timer when the queue is empty.
        """
        now: float = _time.monotonic()
        doc = self._text.document()
        active: list[dict] = []

        for entry in self._fade_queue:
            elapsed: float = now - entry["insert_time"]
            if elapsed >= FADE_DURATION_S:
                # Animation complete — ensure exact base color
                self._apply_format_range(
                    entry["start"], entry["end"], entry["base_color"]
                )
                continue  # Drop from queue

            # Interpolate: bright → base over 1 second
            t: float = elapsed / FADE_DURATION_S
            bright: str = _brighten(entry["base_color"], FADE_BRIGHTNESS)
            current: str = _lerp_color(bright, entry["base_color"], t)
            self._apply_format_range(
                entry["start"], entry["end"], current
            )
            active.append(entry)

        self._fade_queue = active

        # Stop timer when nothing left to animate
        if not self._fade_queue:
            self._fade_timer.stop()

    def _apply_format_range(
        self, start: int, end: int, color_hex: str
    ) -> None:
        """Apply a foreground color to a character range in the document.

        Args:
            start: Start character position
            end: End character position (exclusive)
            color_hex: Hex color string like "#81c784"
        """
        cursor: QTextCursor = QTextCursor(self._text.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt: QTextCharFormat = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        cursor.mergeCharFormat(fmt)

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def _update_status(self) -> None:
        """Update the status label with current counts."""
        plain: str = self._text.toPlainText()
        line_count: int = plain.count("\n") + (1 if plain else 0)
        char_count: int = len(plain)
        self._status_label.setText(
            f"{line_count} lines \u00b7 {char_count:,} chars")

    # -------------------------------------------------------------------------
    # Public Logging API
    # -------------------------------------------------------------------------

    def log_info(self, message: str) -> None:
        """Log an info message (green)."""
        self._append_line(message, "info")

    def log_warn(self, message: str) -> None:
        """Log a warning message (orange)."""
        self._append_line(message, "warn")

    def log_error(self, message: str) -> None:
        """Log an error message (red)."""
        self._append_line(message, "error")

    def log_debug(self, message: str) -> None:
        """Log a debug message (blue)."""
        self._append_line(message, "debug")

    def log_success(self, message: str) -> None:
        """Log a success message (bright green)."""
        self._append_line(message, "success")

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with specified level.

        Args:
            message: The message to log
            level: One of "info", "warn", "error", "debug", "success"
        """
        method = getattr(self, f"log_{level}", self.log_info)
        method(message)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all log messages and stop fade animation."""
        self._fade_timer.stop()
        self._fade_queue.clear()
        self._text.clear()
        self._char_count = 0
        self._update_status()

    def copy_to_clipboard(self) -> None:
        """Copy all log text to system clipboard."""
        text: str = self._text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
            self._status_label.setText("Copied to clipboard!")

    def get_text(self) -> str:
        """Get all log text as plain text.

        Returns:
            Plain text log content
        """
        return self._text.toPlainText()

    def get_html(self) -> str:
        """Get all log text as HTML.

        Returns:
            HTML log content
        """
        return self._text.toHtml()

    def set_max_lines(self, max_lines: int) -> None:
        """DEPRECATED: Use max_chars instead. Sets approximate char limit.

        Args:
            max_lines: Approximate max lines (×80 chars each)
        """
        self._max_chars = max_lines * 80

    def set_max_chars(self, max_chars: int) -> None:
        """Set maximum total characters to keep (0 = unlimited).

        Args:
            max_chars: Character limit
        """
        self._max_chars = max_chars

    def set_show_timestamps(self, show: bool) -> None:
        """Set whether to show timestamps.

        Args:
            show: Whether to show timestamps
        """
        self._show_timestamps = show

    def get_log_callback(self) -> Callable[[str], None]:
        """Get a callback function for logging info messages.

        Returns:
            Callable that logs info messages

        Example:
            callback = log.get_log_callback()
            callback("Some message")
        """
        return self.log_info

    # -------------------------------------------------------------------------
    # Size Control
    # -------------------------------------------------------------------------

    def set_min_height(self, height: int) -> None:
        """Set minimum height of the log widget and text area.

        Args:
            height: Minimum height in pixels
        """
        self._min_height = height
        self._text.setMinimumHeight(height)
        self.setMinimumHeight(height)

    def set_max_height(self, height: int) -> None:
        """Set maximum height of the log widget and text area (0 = no limit).

        Args:
            height: Maximum height in pixels
        """
        self._max_height = height
        if height > 0:
            self.setMaximumHeight(height)
            self._text.setMaximumHeight(height)
        elif height == 0:
            self.setMaximumHeight(16777215)
            self._text.setMaximumHeight(16777215)


__all__ = [
    "QActivityLog",
    "LOG_COLORS",
    "LOG_PREFIXES",
]
