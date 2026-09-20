"""QThemeProvider — Qt singleton that owns the active Theme and emits changes."""
from __future__ import annotations

import threading

from ported.lks_utils.theme.theme import Theme
from ported.lks_utils.theme.theme_registry import ThemeRegistry
from ported.lks_utils.theme.palette import Palette
from ported.lks_utils.theme.metrics import Metrics
from ported.lks_utils.theme.typography import Typography
from ported.lks_utils.gui_qt.theme.color_adapter import to_qcolor
from ported.lks_utils.gui_qt.theme.qpalette_adapter import qpalette_for_theme
from ported.lks_utils.gui_qt.theme.stylesheet_generator import theme_to_qss

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
from PySide6.QtGui import QColor, QPalette


class QThemeProvider(QObject):
    """Application-wide theme provider singleton.

    Emit ``theme_changed`` to notify all theme-aware widgets when
    ``set_current`` is called.

    Usage::

        provider = QThemeProvider.instance()
        provider.set_current_by_name("light")
        qcolor = provider.color("accent")
    """

    theme_changed = Signal(object)  # Theme

    _instance: QThemeProvider | None = None
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> QThemeProvider:
        """Return the singleton, constructing it lazily on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_for_test(cls) -> None:
        """Destroy and clear the singleton (test isolation only)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.deleteLater()
                cls._instance = None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__(None)  # no parent — lives for app lifetime
        self._registry: ThemeRegistry = ThemeRegistry.with_builtins()
        self._current: Theme = self._registry.default()
        self._qpalette_cache: QPalette | None = None
        self._qss_cache: str | None = None
        # Invalidate caches whenever the theme changes
        self.theme_changed.connect(self._invalidate_caches)

    # ------------------------------------------------------------------
    # Theme accessors
    # ------------------------------------------------------------------

    def current(self) -> Theme:
        """Return the currently active theme."""
        return self._current

    def set_current(self, theme: Theme) -> None:
        """Switch to *theme* and emit :attr:`theme_changed`."""
        self._current = theme
        self.theme_changed.emit(self._current)

    def set_current_by_name(self, name: str) -> None:
        """Switch to the registered theme named *name*.

        Raises ``KeyError`` (with available names) if *name* is unknown.
        """
        self.set_current(self._registry.get(name))

    def registry(self) -> ThemeRegistry:
        """Return the underlying :class:`ThemeRegistry`."""
        return self._registry

    # ------------------------------------------------------------------
    # Convenience palette / metrics / typography
    # ------------------------------------------------------------------

    def palette(self) -> Palette:
        """Return the current theme's :class:`Palette`."""
        return self._current.palette

    def metrics(self) -> Metrics:
        """Return the current theme's :class:`Metrics`."""
        return self._current.metrics

    def typography(self) -> Typography:
        """Return the current theme's :class:`Typography`."""
        return self._current.typography

    # ------------------------------------------------------------------
    # QColor lookup
    # ------------------------------------------------------------------

    def color(self, slot: str) -> QColor:
        """Return the ``QColor`` for *slot* in the active palette.

        Raises ``AttributeError`` if the slot name is unknown.
        """
        color_obj = getattr(self._current.palette, slot, None)
        if color_obj is None:
            import dataclasses
            from ported.lks_utils.theme.palette import Palette
            available = [f.name for f in dataclasses.fields(Palette)]
            raise AttributeError(
                f"Unknown palette slot {slot!r}. "
                f"Available slots: {available}"
            )
        return to_qcolor(color_obj)

    # ------------------------------------------------------------------
    # Cached Qt objects
    # ------------------------------------------------------------------

    def qpalette(self) -> QPalette:
        """Return a :class:`QPalette` for the current theme (cached)."""
        if self._qpalette_cache is None:
            self._qpalette_cache = qpalette_for_theme(self._current)
        return self._qpalette_cache

    def qss(self) -> str:
        """Return a QSS stylesheet for the current theme (cached)."""
        if self._qss_cache is None:
            self._qss_cache = theme_to_qss(self._current)
        return self._qss_cache

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _invalidate_caches(self, _theme: object = None) -> None:
        self._qpalette_cache = None
        self._qss_cache = None


__all__ = ["QThemeProvider"]
