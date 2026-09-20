"""Top-level Theme dataclass — immutable composite of Palette, Metrics,
Typography, and optional ThemeExtensions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ported.lks_utils.theme.metrics import Metrics
from ported.lks_utils.theme.palette import Palette
from ported.lks_utils.theme.theme_extension import ThemeExtension
from ported.lks_utils.theme.typography import Typography

_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Theme:
    """Immutable theme snapshot."""

    name: str
    palette: Palette
    metrics: Metrics
    typography: Typography
    extensions: dict[str, ThemeExtension] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "schema_version": _SCHEMA_VERSION,
            "theme": {
                "name": self.name,
                "palette": self.palette.to_dict(),
                "metrics": self.metrics.to_dict(),
                "typography": self.typography.to_dict(),
                "extensions": {
                    k: v.to_dict() for k, v in self.extensions.items()
                },
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> Theme:
        """Accept both the wrapped ``{"schema_version": 1, "theme": {...}}``
        form *and* the bare ``{"name": ..., "palette": ..., ...}`` form
        (hand-written JSON forward compat).
        """
        if "theme" in d:
            inner = d["theme"]
        else:
            inner = d

        name = str(inner["name"])
        palette = Palette.from_dict(inner["palette"])
        metrics = Metrics.from_dict(inner["metrics"])
        typography = Typography.from_dict(inner["typography"])
        raw_ext = inner.get("extensions", {})
        extensions: dict[str, ThemeExtension] = {
            k: ThemeExtension.from_dict(v) for k, v in raw_ext.items()
        }
        return cls(
            name=name,
            palette=palette,
            metrics=metrics,
            typography=typography,
            extensions=extensions,
        )


__all__ = ["Theme"]
