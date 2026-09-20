"""Migrate radial menu configs from schema version 1 to version 2."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _migrate_item(item: dict[str, Any]) -> dict[str, Any]:
    """Infer explicit ``type`` when absent; recurse into children."""
    result: dict[str, Any] = dict(item)

    if "type" not in result:
        children_raw: Any = result.get("children")
        if isinstance(children_raw, list):
            result["type"] = "branch"
        else:
            result["type"] = "action"

    children: Any = result.get("children")
    if isinstance(children, list):
        result["children"] = [
            _migrate_item(child) if isinstance(child, dict) else child
            for child in children
        ]

    return result


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """
    Upgrade a schema-1 config dict to schema 2.

    - Missing ``type``: ``children`` present → ``\"branch\"``, else ``\"action\"``
      (never invent ``\"list\"``; v1 had no lists).
    - Existing ``type`` / ``side`` left unchanged.
    - Top-level ``version`` set to integer ``2``.
    """
    result: dict[str, Any] = deepcopy(data)
    items: Any = result.get("items")
    if isinstance(items, list):
        result["items"] = [
            _migrate_item(item) if isinstance(item, dict) else item
            for item in items
        ]
    result["version"] = 2
    return result
