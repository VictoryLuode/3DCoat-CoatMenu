"""Radial menu schema version constants and normalization."""
from __future__ import annotations

from typing import Any

# Target schema version written by save paths and produced by migrations.
CURRENT_VERSION: int = 3

# Oldest shipped tag used "1.0"; treat missing / that string as schema 1.
_LEGACY_V1_STRINGS: frozenset[str] = frozenset({"1", "1.0"})


def normalize_version(raw: Any) -> int:
    """
    Normalize a config ``version`` field to a sequential integer schema id.

    Rules:
    - Missing / ``None`` → ``1``
    - ``"1.0"`` / ``"1"`` / ``1`` / ``1.0`` → ``1``
    - Integer ``2+`` (or digit string) → that integer
    """
    if raw is None:
        return 1

    if isinstance(raw, bool):
        raise ValueError(
            f"Unrecognized radial menu schema version: {raw!r}"
        )

    if isinstance(raw, int):
        if raw < 1:
            raise ValueError(
                f"Radial menu schema version must be >= 1, got {raw}"
            )
        return raw

    if isinstance(raw, float):
        if raw != int(raw) or raw < 1:
            raise ValueError(
                f"Unrecognized radial menu schema version: {raw!r}"
            )
        return int(raw)

    if isinstance(raw, str):
        text: str = raw.strip()
        if not text:
            return 1
        if text in _LEGACY_V1_STRINGS:
            return 1
        if text.isdigit():
            value: int = int(text)
            if value < 1:
                raise ValueError(
                    f"Radial menu schema version must be >= 1, got {value}"
                )
            return value
        # Allow "2.0" style only when it is a whole number.
        try:
            as_float: float = float(text)
        except ValueError as exc:
            raise ValueError(
                f"Unrecognized radial menu schema version: {raw!r}"
            ) from exc
        if as_float != int(as_float) or as_float < 1:
            raise ValueError(
                f"Unrecognized radial menu schema version: {raw!r}"
            )
        return int(as_float)

    raise ValueError(
        f"Unrecognized radial menu schema version: {raw!r}"
    )
