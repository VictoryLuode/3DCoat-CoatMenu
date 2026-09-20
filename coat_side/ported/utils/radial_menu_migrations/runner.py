"""Sequential radial menu schema migration runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ported.utils.radial_menu_migrations.v1_to_v2 import migrate as migrate_v1_to_v2
from ported.utils.radial_menu_migrations.v2_to_v3 import migrate as migrate_v2_to_v3
from ported.utils.radial_menu_migrations.versions import CURRENT_VERSION, normalize_version

# Maps *from* schema version → step that produces the next version.
# Add ``N: vN_to_vN1.migrate`` when bumping CURRENT_VERSION.
MIGRATION_STEPS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
}


def migrate_config(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Run sequential migrations until ``CURRENT_VERSION``.

    Returns:
        ``(config_dict, migrated)`` where ``migrated`` is True if any step ran.

    Raises:
        ValueError: If version is above CURRENT or a step is missing.
    """
    if not isinstance(data, dict):
        raise ValueError("Radial menu config must be a JSON object")

    version: int = normalize_version(data.get("version"))
    if version > CURRENT_VERSION:
        raise ValueError(
            f"Radial menu schema version {version} is newer than "
            f"supported version {CURRENT_VERSION}"
        )

    if version == CURRENT_VERSION:
        # Normalize stored form to integer CURRENT when already current.
        if data.get("version") != CURRENT_VERSION:
            out: dict[str, Any] = dict(data)
            out["version"] = CURRENT_VERSION
            return out, False
        return data, False

    working: dict[str, Any] = data
    migrated: bool = False
    while version < CURRENT_VERSION:
        step: Callable[[dict[str, Any]], dict[str, Any]] | None = (
            MIGRATION_STEPS.get(version)
        )
        if step is None:
            raise ValueError(
                f"No migration registered from schema version {version} "
                f"toward {CURRENT_VERSION}"
            )
        working = step(working)
        next_version: int = normalize_version(working.get("version"))
        if next_version <= version:
            raise ValueError(
                f"Migration from schema version {version} did not advance "
                f"(still {next_version})"
            )
        version = next_version
        migrated = True

    return working, migrated


def migrate_file(
    path: Path | str,
    *,
    write: bool = True,
) -> tuple[dict[str, Any], bool]:
    """
    Load a radial menu JSON file, migrate in memory, optionally persist.

    When ``write`` is True and migration occurred:
    - Original bytes written to ``path.with_suffix(path.suffix + \".bak\")``
    - Migrated JSON written via ``.tmp`` then atomic replace.
    """
    file_path: Path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Radial menu config not found: {file_path}")

    original_text: str = file_path.read_text(encoding="utf-8")
    raw: Any = json.loads(original_text)
    if not isinstance(raw, dict):
        raise ValueError(
            f"Radial menu config must be a JSON object: {file_path}"
        )

    migrated_data, migrated = migrate_config(raw)

    if migrated and write:
        bak_path: Path = file_path.with_suffix(file_path.suffix + ".bak")
        bak_path.write_text(original_text, encoding="utf-8")

        tmp_path: Path = file_path.with_suffix(file_path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(migrated_data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(file_path)

    return migrated_data, migrated
