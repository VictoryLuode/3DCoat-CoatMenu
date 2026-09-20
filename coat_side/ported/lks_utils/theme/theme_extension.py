"""Module-local theme extension slot bag.

Modules with colour needs that don't belong in the shared ``Palette``
register a ``ThemeExtension`` via ``ThemeRegistry`` (or directly in their
built-in theme JSON). This is an *escape hatch*, not a substitute for
promoting a genuinely shared slot to ``Palette``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ported.lks_utils.theme.color import Color

# Allowed field value types.
_ALLOWED_TYPES = (Color, int, str, bool)
FieldValue = Color | int | str | bool


@dataclass(frozen=True)
class ThemeExtension:
    """Immutable bag of typed theme fields scoped to a module.

    Args:
        module: Dotted module name, e.g. ``"ported.lks_utils.paint"``.
        schema_version: Integer version for the extension schema.
        fields: Mapping from field name to ``Color | int | str | bool``.
    """

    module: str
    schema_version: int
    fields: dict[str, FieldValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for k, v in self.fields.items():
            if not isinstance(v, _ALLOWED_TYPES):
                raise TypeError(
                    f"ThemeExtension field {k!r} has illegal type "
                    f"{type(v).__name__!r}; allowed: Color, int, str, bool"
                )

    # ------------------------------------------------------------------
    # Typed accessors (raise KeyError on miss)
    # ------------------------------------------------------------------

    def get_color(self, name: str) -> Color:
        val = self._get(name)
        if not isinstance(val, Color):
            raise TypeError(
                f"Field {name!r} is not a Color (got {type(val).__name__})")
        return val

    def get_int(self, name: str) -> int:
        val = self._get(name)
        if not isinstance(val, int):
            raise TypeError(
                f"Field {name!r} is not an int (got {type(val).__name__})")
        return val

    def get_str(self, name: str) -> str:
        val = self._get(name)
        if not isinstance(val, str):
            raise TypeError(
                f"Field {name!r} is not a str (got {type(val).__name__})")
        return val

    def get_bool(self, name: str) -> bool:
        val = self._get(name)
        if not isinstance(val, bool):
            raise TypeError(
                f"Field {name!r} is not a bool (got {type(val).__name__})")
        return val

    def _get(self, name: str) -> FieldValue:
        if name not in self.fields:
            raise KeyError(
                f"ThemeExtension({self.module!r}) has no field {name!r}. "
                f"Available: {sorted(self.fields)}"
            )
        return self.fields[name]

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        serialised_fields: dict[str, str | int | bool] = {}
        for k, v in self.fields.items():
            if isinstance(v, Color):
                serialised_fields[k] = v.to_hex()
            else:
                serialised_fields[k] = v
        return {
            "module": self.module,
            "schema_version": self.schema_version,
            "fields": serialised_fields,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ThemeExtension:
        module = str(d["module"])
        schema_version = int(d["schema_version"])
        raw_fields: dict[str, object] = dict(d.get("fields", {}))
        parsed: dict[str, FieldValue] = {}
        for k, v in raw_fields.items():
            if isinstance(v, str) and v.startswith("#"):
                parsed[k] = Color.from_hex(v)
            elif isinstance(v, bool):
                parsed[k] = v
            elif isinstance(v, int):
                parsed[k] = v
            elif isinstance(v, str):
                parsed[k] = v
            else:
                raise TypeError(
                    f"ThemeExtension field {k!r} has unrecognised JSON type "
                    f"{type(v).__name__}"
                )
        return cls(module=module, schema_version=schema_version, fields=parsed)


__all__ = ["ThemeExtension", "FieldValue"]
