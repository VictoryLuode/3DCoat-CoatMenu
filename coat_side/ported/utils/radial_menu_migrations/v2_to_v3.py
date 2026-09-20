"""Migrate radial menu configs from schema version 2 to version 3."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

# Must match ported.utils.radial_menu_config.DEFAULT_MENU_RADIUS
_DEFAULT_RADIUS: int = 128


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """
    Upgrade a schema-2 config dict to schema 3.

    - Add ``radius`` (pie radius in px) when missing; default ``128``.
    - Leave optional ``label`` absent (runtime falls back to filename / name).
    - Top-level ``version`` set to integer ``3``.
    """
    result: dict[str, Any] = deepcopy(data)
    if "radius" not in result:
        result["radius"] = _DEFAULT_RADIUS
    else:
        try:
            result["radius"] = max(1, int(result["radius"]))
        except (TypeError, ValueError):
            result["radius"] = _DEFAULT_RADIUS
    result["version"] = 3
    return result
