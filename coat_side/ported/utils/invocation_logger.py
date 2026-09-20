"""
Invocation Logger - Captures stdout/stderr and logs action invocations.

Provides a singleton logger that:
1. Captures all print() output (stdout/stderr) during action execution
2. Logs every invocation with timestamp, action label, duration, and status
3. Forwards captured output to the ActivityLog Qt widget when available
4. Works correctly even when Qt panel is not yet loaded (buffers messages)

Usage:
    from ported.utils.invocation_logger import InvocationLogger

    logger = InvocationLogger.get_instance()
    logger.set_log_widget(activity_log_widget)  # Connect to panel

    # Context manager for capturing output around an action:
    with logger.capture_invocation("Decimate 50%") as ctx:
        result = do_decimate(0.5)
        ctx.success = True

    # Or use the decorator:
    @logger.log_action("My Action")
    def my_action():
        print("doing work...")
"""
from __future__ import annotations

import io
import sys
import time
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Generator

__all__ = ["InvocationLogger", "get_invocation_logger"]


# =============================================================================
# TYPES
# =============================================================================

# Forward reference for ActivityLog (avoid import when Qt unavailable)
_ActivityLogType = Any


# =============================================================================
# CAPTURE CONTEXT
# =============================================================================

class _CaptureContext:
    """Holds state for one action invocation capture."""

    __slots__ = ("label", "start_time", "success", "stdout_buf", "stderr_buf")

    def __init__(self, label: str) -> None:
        self.label: str = label
        self.start_time: float = time.monotonic()
        self.success: bool = True
        self.stdout_buf: io.StringIO = io.StringIO()
        self.stderr_buf: io.StringIO = io.StringIO()


# =============================================================================
# TEE OUTPUT (writes to original stream + capture buffer + line callback)
# =============================================================================

class _TeeOutput:
    """
    Write to an original stream AND a capture buffer simultaneously.

    Also invokes a per-line callback so we can forward output line-by-line
    to the ActivityLog widget in real time.
    """

    def __init__(
        self,
        original: Any,
        capture: io.StringIO,
        on_line: Callable[[str], None] | None = None,
    ) -> None:
        self._original = original
        self._capture = capture
        self._on_line = on_line
        self._line_buf: str = ""

    def write(self, data: str) -> int:
        if self._original is not None:
            self._original.write(data)
        self._capture.write(data)
        if self._on_line is not None:
            self._line_buf += data
            while "\n" in self._line_buf:
                line, self._line_buf = self._line_buf.split("\n", 1)
                self._on_line(line)
        return len(data)

    def flush(self) -> None:
        if self._original is not None:
            self._original.flush()
        if self._on_line is not None and self._line_buf:
            self._on_line(self._line_buf)
            self._line_buf = ""

    def fileno(self) -> int:
        if self._original is not None:
            return self._original.fileno()
        return -1

    def isatty(self) -> bool:
        if self._original is not None:
            return self._original.isatty()
        return False

    def close(self) -> None:
        self.flush()


# =============================================================================
# INVOCATION LOGGER
# =============================================================================

class InvocationLogger:
    """
    Singleton logger for capturing stdout/stderr and logging action invocations.

    Redirects stdout/stderr during action execution, collects output, and
    forwards it to the ActivityLog Qt widget in the LKS panel.

    When the panel is not yet loaded, output is buffered and flushed when
    the widget reference is set.

    Attributes:
        _instance: Singleton instance
        _log_widget: Reference to ActivityLog widget (set by panel)
        _capture_stack: Stack of active capture contexts (supports nesting)
        _pending_buffer: Buffered messages before widget is connected
    """

    _instance: InvocationLogger | None = None

    def __init__(self) -> None:
        self._log_widget: _ActivityLogType | None = None
        self._capture_stack: list[_CaptureContext] = []
        self._pending_buffer: list[tuple[str, str]] = []  # (level, message)
        self._is_installed: bool = False

    # -------------------------------------------------------------------------
    # Singleton
    # -------------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "InvocationLogger":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Widget Connection
    # -------------------------------------------------------------------------

    def set_log_widget(self, widget: _ActivityLogType) -> None:
        """
        Connect to the ActivityLog widget in the LKS panel.

        Once connected, all captured output is forwarded to the widget.
        Any buffered messages are flushed immediately.

        Args:
            widget: The ActivityLog instance from the main panel
        """
        self._log_widget = widget
        # Flush any pending messages
        for level, msg in self._pending_buffer:
            self._emit(level, msg)
        self._pending_buffer.clear()

    def clear_log_widget(self) -> None:
        """Disconnect from the ActivityLog widget."""
        self._log_widget = None

    # -------------------------------------------------------------------------
    # Internal Output Routing
    # -------------------------------------------------------------------------

    def _emit(self, level: str, message: str) -> None:
        """Route a message to the ActivityLog widget or buffer it."""
        if self._log_widget is not None:
            method = getattr(self._log_widget, f"log_{level}", self._log_widget.log_info)
            method(message)
        else:
            self._pending_buffer.append((level, message))
            # Only print to console if stdout is NOT being captured.
            # During capture (stdout = _TeeOutput), print() would route
            # through _on_stdout_line → _emit → print() → infinite recursion.
            if not self._is_installed and sys.__stdout__ is not None:
                sys.__stdout__.write(f"[InvocationLogger] {message}\n")
                sys.__stdout__.flush()

    def _on_stdout_line(self, line: str) -> None:
        """Callback for each line written to stdout during capture."""
        self._emit("debug", line)

    def _on_stderr_line(self, line: str) -> None:
        """Callback for each line written to stderr during capture."""
        self._emit("error", line)

    # -------------------------------------------------------------------------
    # stdout/stderr Capture
    # -------------------------------------------------------------------------

    @contextmanager
    def capture_invocation(self, label: str) -> Generator[_CaptureContext, None, None]:
        """
        Context manager that captures all stdout/stderr during an action.

        Args:
            label: Human-readable label for this invocation (e.g., "Decimate 50%")

        Yields:
            _CaptureContext - set ctx.success = False on error

        Example:
            with logger.capture_invocation("Resample Half") as ctx:
                try:
                    do_resample(0.5)
                except Exception:
                    ctx.success = False
                    raise
        """
        ctx = _CaptureContext(label)

        # Push onto capture stack (supports nesting)
        self._capture_stack.append(ctx)

        # Install stdout/stderr redirect if this is the outermost capture
        was_installed: bool = self._is_installed
        if not self._is_installed:
            self._install_redirect()

        try:
            yield ctx
        except Exception:
            ctx.success = False
            # Capture the traceback into our stderr buffer
            ctx.stderr_buf.write(traceback.format_exc())
            raise
        finally:
            # Pop from stack
            self._capture_stack.pop()

            # If this was the outermost capture, restore stdout/stderr
            if not self._is_installed or len(self._capture_stack) == 0:
                self._restore_redirect()

            # Compute duration
            duration_ms: float = (time.monotonic() - ctx.start_time) * 1000.0

            # Get captured output
            stdout_text: str = ctx.stdout_buf.getvalue()
            stderr_text: str = ctx.stderr_buf.getvalue()

            # Log the invocation summary
            self._log_invocation(
                label=ctx.label,
                duration_ms=duration_ms,
                success=ctx.success,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
            )

    def _install_redirect(self) -> None:
        """Install stdout/stderr redirection to capture output."""
        if self._is_installed:
            return
        self._is_installed = True

        # Get the innermost (most recent) capture context
        if not self._capture_stack:
            return
        ctx = self._capture_stack[-1]

        sys.stdout = _TeeOutput(
            sys.__stdout__, ctx.stdout_buf, self._on_stdout_line
        )
        sys.stderr = _TeeOutput(
            sys.__stderr__, ctx.stderr_buf, self._on_stderr_line
        )

    def _restore_redirect(self) -> None:
        """Restore original stdout/stderr."""
        if not self._is_installed:
            return
        self._is_installed = False
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    # -------------------------------------------------------------------------
    # Invocation Logging
    # -------------------------------------------------------------------------

    def _log_invocation(
        self,
        label: str,
        duration_ms: float,
        success: bool,
        stdout_text: str,
        stderr_text: str,
    ) -> None:
        """
        Log a completed action invocation to the ActivityLog.

        Emits:
        1. A header line with timestamp, label, duration, status
        2. Full stdout content (if any)
        3. Full stderr content (if any)
        """
        # Header: status icon + label + duration
        status_icon: str = "OK" if success else "FAIL"
        header: str = f"[{status_icon}] {label} ({duration_ms:.0f}ms)"

        level: str = "success" if success else "error"
        self._emit(level, header)

        # Full stdout output
        if stdout_text.strip():
            # Emit each line so it appears in the log
            for line in stdout_text.strip().splitlines():
                self._emit("debug", f"  {line}")

        # Full stderr output
        if stderr_text.strip():
            for line in stderr_text.strip().splitlines():
                self._emit("error", f"  {line}")

    # -------------------------------------------------------------------------
    # Decorator for Logging Functions
    # -------------------------------------------------------------------------

    def log_action(self, label: str) -> Callable:
        """
        Decorator that wraps a function with capture_invocation.

        Args:
            label: Human-readable label for this action

        Returns:
            Decorated function

        Example:
            @logger.log_action("Decimate Selected 50%")
            def decimate_half():
                from ported.ops.SculptObject_Decimate import main as op_main
                op_main(scope=Scope.CURRENT, reduction_percent=50.0)
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                logger = InvocationLogger.get_instance()
                with logger.capture_invocation(label) as ctx:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception:
                        ctx.success = False
                        raise
            return wrapper
        return decorator

    # -------------------------------------------------------------------------
    # Direct Logging (without capture)
    # -------------------------------------------------------------------------

    def log(self, message: str, level: str = "info") -> None:
        """
        Log a simple message directly to the activity log.

        Args:
            message: The message text
            level: One of 'info', 'warn', 'error', 'debug', 'success'
        """
        self._emit(level, message)

    def log_info(self, message: str) -> None:
        self._emit("info", message)

    def log_warn(self, message: str) -> None:
        self._emit("warn", message)

    def log_error(self, message: str) -> None:
        self._emit("error", message)

    def log_debug(self, message: str) -> None:
        self._emit("debug", message)

    def log_success(self, message: str) -> None:
        self._emit("success", message)


# =============================================================================
# MODULE-LEVEL ACCESSOR
# =============================================================================

def get_invocation_logger() -> InvocationLogger:
    """Get the singleton InvocationLogger instance."""
    return InvocationLogger.get_instance()
