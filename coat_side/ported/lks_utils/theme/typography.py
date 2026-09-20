"""Font-family and size slots for a theme.

All sizes in points (pt).  Font families are CSS-style fallback strings.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Typography:
    """Font settings for a theme."""

    ui_family: str
    ui_size_pt: int
    mono_family: str
    mono_size_pt: int
    hud_family: str
    hud_size_pt: int
    heading_size_pt: int
    small_size_pt: int

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, str | int]:
        import dataclasses
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

    @classmethod
    def from_dict(cls, d: dict[str, str | int]) -> Typography:
        import dataclasses
        kwargs: dict[str, str | int] = {}
        for f in dataclasses.fields(cls):
            if f.name not in d:
                raise KeyError(
                    f"Typography: required field {f.name!r} is missing"
                )
            val = d[f.name]
            # sizes must be int
            if f.name.endswith("_pt"):
                kwargs[f.name] = int(val)
            else:
                kwargs[f.name] = str(val)
        return cls(**kwargs)


__all__ = ["Typography"]
