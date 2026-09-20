"""Slim bundled stub for ported.lks_utils.gui_qt.widgets.button_presets (LKS release)."""
from __future__ import annotations

from typing import Any
import importlib

_LAZY_EXPORTS: dict[str, str] = {
    'preset_icon_color': 'ported.lks_utils.gui_qt.widgets.button_presets.icon_loader',
}

__all__ = ['preset_icon_color']

def __getattr__(name: str) -> Any:
    mod_path = _LAZY_EXPORTS.get(name)
    if mod_path is None:
        raise AttributeError(f"module 'ported.lks_utils.gui_qt.widgets.button_presets' "
            f"has no attribute {name!r}")
    mod = importlib.import_module(mod_path)
    value = getattr(mod, name)
    globals()[name] = value
    return value
