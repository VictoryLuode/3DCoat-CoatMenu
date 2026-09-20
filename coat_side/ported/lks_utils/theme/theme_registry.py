"""Named-theme registry with a default pointer.

Not a singleton — Stage 2 wraps the active-theme singleton in
``QThemeProvider``.  The registry is just a typed dict + default name.
"""
from __future__ import annotations

from ported.lks_utils.theme.theme import Theme


class ThemeRegistry:
    """Maps theme names to ``Theme`` instances and tracks a default."""

    def __init__(self) -> None:
        self._themes: dict[str, Theme] = {}
        self._default: str | None = None

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, theme: Theme) -> None:
        """Register *theme*.  Raises ``ValueError`` on duplicate name."""
        if theme.name in self._themes:
            raise ValueError(
                f"ThemeRegistry: theme {theme.name!r} is already registered. "
                f"Available: {sorted(self._themes)}"
            )
        self._themes[theme.name] = theme
        if self._default is None:
            self._default = theme.name

    def set_default(self, name: str) -> None:
        """Set the default theme by name.  Raises ``KeyError`` if unknown."""
        self._require(name)
        self._default = name

    def unregister(self, name: str) -> None:
        """Remove *name* from the registry.  Raises ``KeyError`` if unknown.

        If the removed theme was the default, the default is re-pointed to
        the first remaining theme (alphabetically), or ``None`` if empty.
        """
        self._require(name)
        del self._themes[name]
        if self._default == name:
            remaining = sorted(self._themes)
            self._default = remaining[0] if remaining else None

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> Theme:
        """Return the theme by name.  Raises ``KeyError`` listing alternatives."""
        return self._themes[self._require(name)]

    def default(self) -> Theme:
        """Return the current default theme.  Raises if registry is empty."""
        if self._default is None:
            raise RuntimeError(
                "ThemeRegistry is empty — no default theme set.")
        return self._themes[self._default]

    def names(self) -> list[str]:
        """Return sorted list of registered theme names."""
        return sorted(self._themes)

    def __contains__(self, name: str) -> bool:
        return name in self._themes

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @classmethod
    def with_builtins(cls) -> ThemeRegistry:
        """Return a ``ThemeRegistry`` pre-loaded with the three built-in themes."""
        from ported.lks_utils.theme.theme_io import load_builtin_themes

        registry = cls()
        for theme in load_builtin_themes():
            registry.register(theme)
        registry.set_default("dark")
        return registry

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _require(self, name: str) -> str:
        if name not in self._themes:
            raise KeyError(
                f"ThemeRegistry: theme {name!r} not found. "
                f"Available: {sorted(self._themes)}"
            )
        return name


__all__ = ["ThemeRegistry"]
