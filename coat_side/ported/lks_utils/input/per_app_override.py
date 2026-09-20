"""Per-app binding override file I/O.

Override files live at ``~/.ported.lks_utils/<app_name>/bindings.json`` and contain
only the user-modified bindings (sparse format).  The process-wide
``InputBindings`` registry supplies defaults; this module stores the delta.

Schema (version 1)::

    {
        "schema_version": 1,
        "app_name": "<app_name>",
        "overrides": {
            "<action_id>": [<binding_dict>, ...]
        }
    }
"""
from __future__ import annotations

import json
from pathlib import Path

from ported.lks_utils.core import atomic_write
from ported.lks_utils.input.binding import (
    Binding,
    GestureKind,
    KeyBinding,
    Modifier,
    MouseBinding,
    MouseButton,
    WheelBinding,
)


def overrides_path(app_name: str) -> Path:
    """Return the path to ``<app_name>``'s bindings override file.

    Location: ``~/.ported.lks_utils/<app_name>/bindings.json``.
    """
    return Path.home() / ".ported.lks_utils" / app_name / "bindings.json"


def load_per_app_overrides(app_name: str) -> dict[str, list[Binding]]:
    """Load the per-app override file.

    Returns an empty dict if the file does not exist.

    Raises:
        ValueError: If the file exists but cannot be parsed as valid JSON or
            has an unsupported schema_version.  The exception message includes
            the file path.
    """
    path = overrides_path(app_name)
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse bindings override file {path}: {exc}"
        ) from exc

    version = data.get("schema_version")
    if version != 1:
        raise ValueError(
            f"Unsupported bindings schema_version {version!r} in {path}"
        )

    overrides: dict[str, list[Binding]] = {}
    for action_id, raw_list in data.get("overrides", {}).items():
        overrides[action_id] = [_binding_from_dict(d) for d in raw_list]
    return overrides


def save_per_app_overrides(
    app_name: str,
    overrides: dict[str, list[Binding]],
) -> None:
    """Write the per-app override file (sparse — defaults are NOT stored).

    Uses an atomic write so a crash during saving cannot corrupt the file.
    """
    path = overrides_path(app_name)
    payload: dict = {
        "schema_version": 1,
        "app_name": app_name,
        "overrides": {
            action_id: [_binding_to_dict(b) for b in bindings]
            for action_id, bindings in overrides.items()
        },
    }
    atomic_write(str(path), json.dumps(payload, indent=2), encoding="utf-8")


# ── Private serialisation helpers ────────────────────────────────────────────

def _binding_to_dict(b: Binding) -> dict:
    if isinstance(b, KeyBinding):
        return {"kind": "key", "key": b.key}
    if isinstance(b, MouseBinding):
        return {
            "kind": "mouse",
            "button": b.button.value,
            "modifiers": sorted(m.value for m in b.modifiers),
            "gesture": b.gesture.value,
        }
    if isinstance(b, WheelBinding):
        return {
            "kind": "wheel",
            "modifiers": sorted(m.value for m in b.modifiers),
            "direction": b.direction,
        }
    raise TypeError(f"unknown binding type: {type(b).__name__}")


def _binding_from_dict(d: dict) -> Binding:
    kind = d.get("kind")
    if kind == "key":
        return KeyBinding(key=d["key"])
    if kind == "mouse":
        return MouseBinding(
            button=MouseButton(d["button"]),
            modifiers=frozenset(Modifier(m) for m in d.get("modifiers", [])),
            gesture=GestureKind(d.get("gesture", "press")),
        )
    if kind == "wheel":
        return WheelBinding(
            modifiers=frozenset(Modifier(m) for m in d.get("modifiers", [])),
            direction=d.get("direction", "any"),
        )
    raise ValueError(f"unknown binding kind: {kind!r}")


__all__ = [
    "overrides_path",
    "load_per_app_overrides",
    "save_per_app_overrides",
]
