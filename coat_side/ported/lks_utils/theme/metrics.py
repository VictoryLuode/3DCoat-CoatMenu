"""Integer-pixel metrics for layout, borders, radii, and spacing.

Resolution-independent: DPR scaling is the renderer's job.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metrics:
    """Integer-pixel layout metrics for a theme."""

    grid_minor_px: int
    grid_major_px: int
    border_px: int
    selection_outline_px: int
    handle_radius_px: int
    button_radius_px: int
    panel_radius_px: int
    focus_ring_px: int
    spacing_xs: int
    spacing_sm: int
    spacing_md: int
    spacing_lg: int
    validation_badge_size_px: int

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, int]:
        import dataclasses
        return {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> Metrics:
        import dataclasses
        kwargs: dict[str, int] = {}
        for f in dataclasses.fields(cls):
            if f.name not in d:
                raise KeyError(
                    f"Metrics: required field {f.name!r} is missing")
            kwargs[f.name] = int(d[f.name])
        return cls(**kwargs)


__all__ = ["Metrics"]
