"""Application-level singleton that holds the live InputBindings registry.

The singleton is constructed once per Qt application. On construction it:

1. Loads the default registry via ``ported.lks_utils.input.get_default_bindings()``.
2. Reads per-app user overrides from
   ``~/.ported.lks_utils/<app_name>/bindings.json`` (if present).
3. Applies the overrides via ``InputBindings.with_overrides``.

Any subsequent mutation (``set_user_override``, ``reset_to_defaults``) fires
the ``bindings_changed`` signal so interested widgets can refresh.

Thread safety: all public methods must be called from the GUI thread.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from ported.lks_utils.input import (
    Action,
    Binding,
    InputBindings,
    get_default_bindings,
    load_per_app_overrides,
    save_per_app_overrides,
)

if TYPE_CHECKING:
    pass

# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: QInputBindingsProvider | None = None


class QInputBindingsProvider(QObject):
    """Application-wide live registry of input bindings.

    Usage::

        provider = QInputBindingsProvider.instance()
        bindings = provider.bindings()
    """

    bindings_changed = Signal(InputBindings)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._app_name: str = self._resolve_app_name()
        self._defaults: InputBindings = get_default_bindings()
        self._user_overrides: dict[str, list[Binding]] = {}
        self._bindings: InputBindings = self._defaults

        # Load per-app overrides from disk and apply
        stored = load_per_app_overrides(self._app_name)
        if stored:
            self._user_overrides = dict(stored)
            self._apply_overrides()

    # ── Singleton access ──────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> QInputBindingsProvider:
        """Return (or create) the process-wide singleton."""
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    # ── Public API ────────────────────────────────────────────────────────────

    def bindings(self) -> InputBindings:
        """Return the current live registry."""
        return self._bindings

    def set_bindings(self, bindings: InputBindings) -> None:
        """Replace the entire registry and emit ``bindings_changed``.

        Also updates the internal defaults so subsequent ``set_user_override``
        calls apply on top of the new registry.
        """
        self._defaults = bindings
        self._user_overrides = {}
        self._bindings = bindings
        self.bindings_changed.emit(self._bindings)

    def set_user_override(self, action: Action, bindings: list[Binding]) -> None:
        """Override the bindings for *action* and emit ``bindings_changed``."""
        self._user_overrides[action.id] = list(bindings)
        self._apply_overrides()
        self.bindings_changed.emit(self._bindings)

    def clear_user_override(self, action: Action) -> None:
        """Remove the user override for *action* and emit ``bindings_changed``."""
        if action.id in self._user_overrides:
            del self._user_overrides[action.id]
            self._apply_overrides()
            self.bindings_changed.emit(self._bindings)

    def reset_to_defaults(self) -> None:
        """Discard all user overrides and reset to the compiled defaults."""
        self._user_overrides = {}
        self._bindings = self._defaults
        # Also clear the on-disk file by saving an empty override set
        save_per_app_overrides(self._app_name, {})
        self.bindings_changed.emit(self._bindings)

    def save_user_overrides(self) -> None:
        """Persist current user overrides to ``~/.ported.lks_utils/<app>/bindings.json``.

        Only stores bindings that differ from the compiled defaults.
        """
        diff: dict[str, list[Binding]] = {}
        for action_id, user_bindings in self._user_overrides.items():
            entry = self._defaults._actions.get(
                action_id)  # type: ignore[attr-defined]
            if entry is None:
                continue
            default_bindings = list(entry.current)
            if list(user_bindings) != default_bindings:
                diff[action_id] = user_bindings
        save_per_app_overrides(self._app_name, diff)

    # ── Test hook ─────────────────────────────────────────────────────────────

    @classmethod
    def _reset_for_test(cls) -> None:
        """Destroy the singleton so the next ``instance()`` call rebuilds it.

        Only for use in tests. Never call from production code.
        """
        global _instance
        if _instance is not None:
            _instance.deleteLater()
            _instance = None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _resolve_app_name(self) -> str:
        """Return QApplication.applicationName(), falling back to 'ported.lks_utils'."""
        app = QApplication.instance()
        if app is not None:
            name = app.applicationName()
            if name:
                return name
        return "ported.lks_utils"

    def _apply_overrides(self) -> None:
        """Rebuild ``_bindings`` from defaults + current user overrides."""
        if not self._user_overrides:
            self._bindings = self._defaults
            return

        # Build an Action→[Binding] map for with_overrides
        overrides: dict[Action, list[Binding]] = {}
        for action_id, bindings in self._user_overrides.items():
            entry = self._defaults._actions.get(
                action_id)  # type: ignore[attr-defined]
            if entry is not None:
                overrides[entry.action] = bindings

        self._bindings = self._defaults.with_overrides(overrides=overrides)
