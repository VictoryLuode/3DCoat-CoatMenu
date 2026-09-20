"""ThemeAwareMixin — auto-subscribe a QWidget to QThemeProvider changes."""
from __future__ import annotations

from ported.lks_utils.theme.theme import Theme


class ThemeAwareMixin:
    """Mix into a ``QWidget`` subclass to receive theme-change notifications.

    Two usage patterns:

    **Read-on-paint** (simplest): just mix in and let ``update()`` be called
    automatically.  Your ``paintEvent`` reads from
    ``QThemeProvider.instance()`` on every repaint.

    **Cache-on-change** (slightly faster): override
    :meth:`on_theme_changed` to pre-compute colours / pens once per
    theme switch and store them as attributes.

    Example::

        class MyWidget(ThemeAwareMixin, QWidget):
            def __init__(self):
                super().__init__()
                # initial colours picked up in first paintEvent

            def on_theme_changed(self, theme: Theme) -> None:
                self._bg = QThemeProvider.instance().color("canvas_bg")
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider
        provider = QThemeProvider.instance()
        provider.theme_changed.connect(self._on_theme_changed_internal)
        # Disconnect cleanly when the widget is destroyed
        # type: ignore[attr-defined]
        self.destroyed.connect(self._disconnect_theme)

    # ------------------------------------------------------------------
    # Public override point
    # ------------------------------------------------------------------

    def on_theme_changed(self, theme: Theme) -> None:
        """Called on every theme switch while this widget exists.

        Default is a no-op.  Override to pre-compute colour objects.
        """

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_theme_changed_internal(self, theme: object) -> None:
        self.on_theme_changed(theme)  # type: ignore[arg-type]
        self.update()  # type: ignore[attr-defined]

    def _disconnect_theme(self) -> None:
        try:
            from ported.lks_utils.gui_qt.theme.theme_provider import QThemeProvider
            QThemeProvider.instance().theme_changed.disconnect(
                self._on_theme_changed_internal
            )
        except (RuntimeError, TypeError):
            pass


__all__ = ["ThemeAwareMixin"]
