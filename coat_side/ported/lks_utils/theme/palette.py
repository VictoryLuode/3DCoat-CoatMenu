"""Semantic colour palette for all ported.lks_utils GUI themes.

Adding a slot: add one field here (with a default in ``Palette.defaults()``)
and update every built-in JSON file.  Naming rule: describes *meaning*,
never module (e.g. ``selection`` not ``canvas2d_selection``).
"""
from __future__ import annotations

from dataclasses import dataclass

from ported.lks_utils.theme.color import Color


@dataclass(frozen=True)
class Palette:
    """Semantic colour slots for a theme.  All ~30 fields are required.

    Consumers should read named fields (``palette.canvas_bg``), never
    index by string at runtime — use ``ThemeProvider.color(slot)`` for
    that convenience.
    """

    # ---- Surfaces ----
    canvas_bg: Color
    panel_bg: Color
    panel_bg_alt: Color
    overlay_bg: Color

    # ---- Text ----
    text_primary: Color
    text_muted: Color
    text_disabled: Color
    text_inverse: Color

    # ---- Lines & borders ----
    border: Color
    border_strong: Color
    grid_minor: Color
    grid_major: Color
    handle: Color

    # ---- Item / data ----
    item_outline: Color
    item_fill: Color
    item_outline_hover: Color

    # ---- Interaction ----
    selection: Color
    selection_outline: Color
    snap_indicator: Color
    drop_target: Color

    # ---- Status ----
    accent: Color
    success: Color
    warning: Color
    error: Color
    info: Color

    # ---- Controls (chrome) ----
    button_bg: Color
    button_bg_hover: Color
    button_bg_pressed: Color
    button_fg: Color
    input_bg: Color
    input_fg: Color
    input_border: Color

    # ---- Validation badges ----
    validation_invalid: Color

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, str]:
        """Serialise all fields to ``{slot_name: hex_string}``."""
        import dataclasses
        return {
            f.name: getattr(self, f.name).to_dict()
            for f in dataclasses.fields(self)
        }

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Palette:
        """Deserialise.  Missing required fields raise ``KeyError``; unknown
        fields are silently ignored (forward compatibility).
        """
        import dataclasses
        kwargs: dict[str, Color] = {}
        for f in dataclasses.fields(cls):
            if f.name not in d:
                raise KeyError(
                    f"Palette: required field {f.name!r} is missing"
                )
            kwargs[f.name] = Color.from_dict(d[f.name])
        return cls(**kwargs)


__all__ = ["Palette"]
