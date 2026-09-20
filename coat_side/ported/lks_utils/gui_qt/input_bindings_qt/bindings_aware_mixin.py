"""Mixin that connects a Qt widget to the live bindings provider.

Any ``QWidget`` (or ``QObject``) subclass that also inherits from
``BindingsAwareMixin`` will automatically receive ``on_bindings_changed``
callbacks whenever the application-wide ``InputBindings`` registry is
replaced or updated.

Usage::

    class MyCanvas(QWidget, BindingsAwareMixin):
        def __init__(self, parent=None):
            super().__init__(parent)   # MRO calls BindingsAwareMixin.__init__

        def on_bindings_changed(self, bindings: InputBindings) -> None:
            self._bindings = bindings
            self.update()
"""
from __future__ import annotations

from ported.lks_utils.input import InputBindings


class BindingsAwareMixin:
    """Auto-subscribe to ``QInputBindingsProvider.bindings_changed``.

    Designed for multiple inheritance with ``QWidget`` or ``QObject``.
    The mixin does **not** import ``QInputBindingsProvider`` at module
    level; it imports lazily inside ``__init__`` so that pure-Python
    tests that never instantiate a ``QApplication`` can still import
    this file without side effects.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]
        from ported.lks_utils.gui_qt.input_bindings_qt.input_bindings_provider_qt import (
            QInputBindingsProvider,
        )

        provider = QInputBindingsProvider.instance()
        provider.bindings_changed.connect(self._on_bindings_changed_internal)

        # Disconnect cleanly when this object is destroyed
        # ``destroyed`` is a QObject signal; works with any QObject subclass.
        # In PySide6 cooperative MRO the signal may not be ready yet inside
        # __init__, so schedule the connection for after full construction.
        try:
            from PySide6.QtCore import QTimer
            # type: ignore[arg-type]
            QTimer.singleShot(0, lambda: self._connect_destroyed_signal())
        except Exception:
            # Fallback: try directly (may fail if not a QObject)
            try:
                # type: ignore[attr-defined]
                self.destroyed.connect(self._disconnect_bindings)
            except (AttributeError, RuntimeError):
                pass

    # ── Internal slot ─────────────────────────────────────────────────────────

    def _connect_destroyed_signal(self) -> None:
        """Connect the destroyed signal; called after full construction."""
        try:
            # type: ignore[attr-defined]
            self.destroyed.connect(self._disconnect_bindings)
        except (AttributeError, RuntimeError):
            pass

    def _on_bindings_changed_internal(self, bindings: InputBindings) -> None:
        self.on_bindings_changed(bindings)

    def _disconnect_bindings(self) -> None:
        from ported.lks_utils.gui_qt.input_bindings_qt.input_bindings_provider_qt import (
            QInputBindingsProvider,
        )

        provider = QInputBindingsProvider.instance()
        try:
            provider.bindings_changed.disconnect(
                self._on_bindings_changed_internal)
        except RuntimeError:
            pass  # Already disconnected

    # ── Override point ────────────────────────────────────────────────────────

    def on_bindings_changed(self, bindings: InputBindings) -> None:
        """Called whenever the application bindings change.

        Override in subclasses to react to remaps (e.g. refresh tooltips,
        rebuild context menus). Default is a no-op — the next input event
        resolves via the new registry automatically.
        """
