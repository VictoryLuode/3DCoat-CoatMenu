"""Extension identity helpers for side-by-side installs.

3DCoat cExtensions live in ``cExtensions/<FolderName>/`` and Start loads
``<FolderName>.py``. Side-test packs may use names other than ``LKS``.
"""
from __future__ import annotations

from pathlib import Path


def get_extension_root() -> Path:
    """Return this install's cExtension root (parent of ``ported.utils/``)."""
    return Path(__file__).resolve().parent.parent


def get_extension_folder_name() -> str:
    """Return the cExtension folder name (``LKS``, ``LKS_Side``, …)."""
    return get_extension_root().name


def cextension_module_prefixes() -> tuple[str, ...]:
    """sys.modules prefixes 3DCoat may use for this install."""
    name: str = get_extension_folder_name()
    return (
        f"cExtensions.{name}.",
        f"cModules.{name}.",
        # Always include classic LKS prefixes for mixed/dev layouts
        "cExtensions.LKS.",
        "cModules.LKS.",
    )


def action_module_strip_prefixes() -> tuple[str, ...]:
    """Prefixes to strip when deriving action labels from ``__module__``."""
    name: str = get_extension_folder_name()
    return (
        f"cExtensions.{name}.actions.",
        f"cExtensions.{name}.radial.",
        f"cExtensions.{name}.",
        "cExtensions.LKS.actions.",
        "cExtensions.LKS.radial.",
        "cExtensions.LKS.",
        "actions.",
    )
