"""Color value type — framework-agnostic, zero Qt imports.

A frozen dataclass encoding an RGBA colour as four 0–255 integers.
JSON encoding is always an 8-digit hex string (``#RRGGBBAA``) for
human-readable theme files.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    """Immutable RGBA colour. Components are 0–255 integers."""

    r: int
    g: int
    b: int
    a: int = 255

    def __post_init__(self) -> None:
        for name, val in (("r", self.r), ("g", self.g), ("b", self.b), ("a", self.a)):
            if not isinstance(val, int):
                raise TypeError(
                    f"Color.{name} must be int, got {type(val).__name__}")
            if not (0 <= val <= 255):
                raise ValueError(
                    f"Color.{name} out of range: {val!r} (must be 0–255)"
                )

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_hex(cls, hex_str: str) -> Color:
        """Parse ``#RRGGBB`` or ``#RRGGBBAA``.

        Short forms (``#RGB``, ``#RGBA``) are NOT accepted; a ``ValueError``
        is raised to avoid silent precision loss.
        """
        s = hex_str.strip()
        if not s.startswith("#"):
            raise ValueError(
                f"Color hex string must start with '#': {hex_str!r}")
        body = s[1:]
        if len(body) == 6:
            r = int(body[0:2], 16)
            g = int(body[2:4], 16)
            b = int(body[4:6], 16)
            return cls(r, g, b, 255)
        elif len(body) == 8:
            r = int(body[0:2], 16)
            g = int(body[2:4], 16)
            b = int(body[4:6], 16)
            a = int(body[6:8], 16)
            return cls(r, g, b, a)
        else:
            raise ValueError(
                f"Color.from_hex requires #RRGGBB or #RRGGBBAA, got {hex_str!r}"
            )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_hex(self) -> str:
        """Return always-8-digit ``#RRGGBBAA`` form."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"

    def to_dict(self) -> str:
        """Serialise as hex string (compatible with ``from_dict``)."""
        return self.to_hex()

    @classmethod
    def from_dict(cls, raw: str) -> Color:
        """Deserialise from a hex string produced by ``to_dict``."""
        return cls.from_hex(raw)

    # ------------------------------------------------------------------
    # Mutation helpers (return new instances)
    # ------------------------------------------------------------------

    def with_alpha(self, a: int) -> Color:
        """Return a new ``Color`` with the given alpha value."""
        return Color(self.r, self.g, self.b, a)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})"


__all__ = ["Color"]
