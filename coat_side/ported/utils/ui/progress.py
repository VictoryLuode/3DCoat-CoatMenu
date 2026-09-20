"""Shared progress/iteration context factory for UI sections."""
from __future__ import annotations
from typing import Callable
from ported.utils.scope_utils import IterationContext


def make_iteration_context(
    action_verb: str,
    log_info: Callable[[str], None],
    log_success: Callable[[str], None] | None = None,
) -> IterationContext:
    """Create an IterationContext wired to the ActivityLog.

    Args:
        action_verb: "Decimating", "Voxelizing", "Converting", etc.
        log_info: Function that logs to ActivityLog info channel
        log_success: Optional function that logs to ActivityLog success channel

    Returns:
        IterationContext with progress callbacks wired to the log.
    """
    def on_progress(index: int, total: int, name: str) -> None:
        log_info(f"  {action_verb} '{name}' ({index + 1}/{total})...")

    def on_start(msg: str) -> None:
        log_info(msg)

    def on_complete(msg: str) -> None:
        if log_success:
            log_success(msg)
        else:
            log_info(msg)

    return IterationContext(
        action_verb=action_verb,
        on_progress=on_progress,
        on_start=on_start,
        on_complete=on_complete,
    )
