"""Hold-and-retry helpers for transient Windows file-lock contention."""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

# Total wall-clock budget for one logical I/O operation (replace, append, unlink).
DEFAULT_FILE_LOCK_MAX_WAIT_SEC: float = 5.0
DEFAULT_FILE_LOCK_INITIAL_BACKOFF_SEC: float = 0.025
DEFAULT_FILE_LOCK_MAX_BACKOFF_SEC: float = 0.25

_T = TypeVar("_T")


def is_transient_file_lock_error(exc: BaseException) -> bool:
    """Return True when a short wait may allow the same I/O to succeed."""
    if isinstance(exc, PermissionError):
        return True
    if not isinstance(exc, OSError):
        return False
    winerror = getattr(exc, "winerror", None)
    if winerror in (5, 32):  # access denied, sharing violation
        return True
    return exc.errno in (5, 13, 32)


def hold_and_retry_io(
    fn: Callable[[], _T],
    *,
    max_wait_sec: float = DEFAULT_FILE_LOCK_MAX_WAIT_SEC,
    initial_backoff_sec: float = DEFAULT_FILE_LOCK_INITIAL_BACKOFF_SEC,
    max_backoff_sec: float = DEFAULT_FILE_LOCK_MAX_BACKOFF_SEC,
) -> _T:
    """Run *fn*, retrying only on transient file-lock errors until *max_wait_sec*."""
    deadline = time.monotonic() + max_wait_sec
    delay = initial_backoff_sec
    last_error: BaseException | None = None
    while True:
        try:
            return fn()
        except BaseException as exc:
            if not is_transient_file_lock_error(exc):
                raise
            last_error = exc
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                break
            time.sleep(min(delay, remaining, max_backoff_sec))
            delay = min(delay * 2.0, max_backoff_sec)
    assert last_error is not None
    raise last_error


def retrying_unlink(path: Path, *, missing_ok: bool = False) -> None:
    """Delete *path*, retrying transient lock errors (Windows stale-file cleanup)."""

    def _unlink() -> None:
        path.unlink(missing_ok=missing_ok)

    hold_and_retry_io(_unlink)
