"""
Base class and decorator for LKS action scripts.

Provides automatic hot-reload, invocation logging with stdout/stderr capture,
and consistent behavior for all action scripts.

Usage (decorator - simplest):
    from ported.utils.action_base import action

    @action(label="Decimate 50%")
    def main():
        from ported.ops.SculptObject_Decimate import main as op_main
        from ported.utils.scope_utils import Scope
        op_main(scope=Scope.CURRENT, reduction_percent=50.0)

    main()

Usage (class - more features):
    from ported.utils.action_base import Action

    class DecimateHalfSelected(Action):
        '''Decimate selected to 50%.'''
        room = "Sculpt"

        def execute(self) -> None:
            from ported.ops.SculptObject_Decimate import main as op_main
            from ported.utils.scope_utils import Scope
            op_main(scope=Scope.CURRENT, reduction_percent=50.0)

    DecimateHalfSelected().run()
"""
from __future__ import annotations

import functools
import inspect
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


# =============================================================================
# LABEL DERIVATION
# =============================================================================

def _derive_label(func: Callable) -> str:
    """
    Derive a human-readable label for an action function.

    Tries:
    1. The function's docstring (first line)
    2. The module name with prefix stripped
    3. The function name as fallback
    """
    # Try docstring
    if func.__doc__:
        first_line: str = func.__doc__.strip().split("\n")[0].strip()
        if first_line and len(first_line) < 80:
            return first_line

    # Try module name
    module: str = getattr(func, "__module__", "")
    if module:
        from ported.utils.extension_identity import action_module_strip_prefixes

        for prefix in action_module_strip_prefixes():
            if module.startswith(prefix):
                return module[len(prefix):]
        return module

    # Fallback to function name
    return func.__name__


# =============================================================================
# DECORATOR (simplest approach)
# =============================================================================

def _optional_hot_reload():
    """Hot reload is a development convenience, not a runtime need.

    It used to come from the add-on this tree was ported out of. If that module is
    not here, reloading is simply skipped - the decorated action still runs.
    """
    try:
        from ported.utils.hot_reload import reload_all
    except ImportError:
        return lambda *args, **kwargs: None
    return reload_all


def action(func: F | None = None, *, label: str | None = None) -> F:
    """
    Decorator that adds hot-reload and invocation logging before running an action.

    Usage:
        @action
        def main():
            from ported.ops.SomeOperator import main as op_main
            op_main(...)

        # Or with explicit label:
        @action(label="Decimate 50%")
        def main():
            ...

        main()
    """
    # Support both @action and @action(label="...")
    if func is None:
        return lambda f: action(f, label=label)  # type: ignore

    resolved_label: str = label or _derive_label(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        reload_all = _optional_hot_reload()

        reload_all()

        # Execute the action with invocation logging
        from ported.utils.invocation_logger import get_invocation_logger

        logger = get_invocation_logger()
        try:
            with logger.capture_invocation(resolved_label) as ctx:
                result = func(*args, **kwargs)
                return result
        except Exception:
            # capture_invocation handles success=False and stderr capture
            raise
        finally:
            # Queue the calling module for cache clearing
            # The LKS extension's postprocess() will clear it next frame
            _queue_module_for_clearing()

    return wrapper  # type: ignore


def _queue_module_for_clearing() -> None:
    """
    Queue action script modules for deferred cache clearing.

    3DCoat imports scripts as Python modules. Python caches these in sys.modules,
    so subsequent menu clicks don't re-execute the file.

    We can't delete immediately because Python's import machinery is still on
    the call stack. Instead, we queue module names and the LKS extension's
    postprocess() hook clears them on the next frame.
    """
    import sys

    # Initialize the queue if needed
    if not hasattr(sys, "_lks_modules_to_clear"):
        sys._lks_modules_to_clear = set()

    # Find and queue action script modules for clearing
    # Imported as "cExtensions.<Folder>.actions.<ScriptName>"
    from ported.utils.extension_identity import get_extension_folder_name

    folder: str = get_extension_folder_name()
    action_markers: tuple[str, ...] = (
        f"cExtensions.{folder}.actions.",
        "cExtensions.LKS.actions.",
    )
    for name in list(sys.modules.keys()):
        if any(marker in name for marker in action_markers):
            sys._lks_modules_to_clear.add(name)


# =============================================================================
# BASE CLASS (more features)
# =============================================================================

class Action:
    """
    Base class for action scripts with automatic hot-reload and invocation logging.

    Subclass and override execute() to implement your action.

    Attributes:
        room: Optional room name. If set, validates we're in that room.
        silent_reload: If True (default), suppress reload output.
        label: Optional label override (default: derived from class docstring/name).

    Example:
        class MyAction(Action):
            '''Decimate selected to 50%.'''
            room = "Sculpt"

            def execute(self) -> None:
                from ported.ops.SomeOperator import main as op_main
                op_main(...)

        MyAction().run()
    """

    room: str | None = None
    silent_reload: bool = True
    label: str | None = None

    def execute(self) -> None:
        """Override this to implement the action logic."""
        raise NotImplementedError("Subclasses must implement execute()")

    def run(self) -> None:
        """Run the action with hot-reload, invocation logging, and optional room validation."""
        # Hot reload all LKS modules
        reload_all = _optional_hot_reload()

        reload_all(silent=self.silent_reload)

        # Validate room if specified
        if self.room is not None:
            self._validate_room()

        # Derive label
        resolved_label: str = self.label or self._derive_class_label()

        # Execute with invocation logging
        from ported.utils.invocation_logger import get_invocation_logger

        logger = get_invocation_logger()
        try:
            with logger.capture_invocation(resolved_label) as ctx:
                self.execute()
        except Exception:
            raise
        finally:
            # Queue for cache clearing (same as @action decorator)
            _queue_module_for_clearing()

    def _derive_class_label(self) -> str:
        """Derive a human-readable label from the class."""
        # Try class docstring
        if self.__class__.__doc__:
            first_line: str = (
                self.__class__.__doc__.strip().split("\n")[0].strip()
            )
            if first_line and len(first_line) < 80:
                return first_line

        # Try module name from class
        module: str = getattr(self.__class__, "__module__", "")
        if module:
            from ported.utils.extension_identity import action_module_strip_prefixes

            for prefix in action_module_strip_prefixes():
                if module.startswith(prefix):
                    return module[len(prefix):]
            return module

        # Fallback to class name
        return self.__class__.__name__

    def _validate_room(self) -> None:
        """Validate we're in the expected room."""
        try:
            import coat

            current_room: str = coat.ui.currentRoom()
            if current_room != self.room:
                coat.ui.showInfoMessage(
                    f"This action requires {self.room} room (current: {current_room})",
                    3000,
                )
                raise RuntimeError(
                    f"Wrong room: expected {self.room}, got {current_room}"
                )
        except ImportError:
            pass  # Running outside 3DCoat (testing)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_action(func: Callable[[], None], label: str | None = None) -> None:
    """
    Run a function as an action with hot-reload and invocation logging.

    Convenience function for one-liners:
        run_action(lambda: op_main(scope=Scope.CURRENT), label="Decimate")
    """
    reload_all = _optional_hot_reload()
    from ported.utils.invocation_logger import get_invocation_logger

    reload_all()
    resolved_label: str = label or _derive_label(func)
    logger = get_invocation_logger()
    with logger.capture_invocation(resolved_label):
        func()
