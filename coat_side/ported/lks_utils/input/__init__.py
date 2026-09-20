"""Slim bundled stub for ported.lks_utils.input (LKS release)."""
from __future__ import annotations

from typing import Any
import importlib

_LAZY_EXPORTS: dict[str, str] = {
    'Action': 'ported.lks_utils.input.action',
    'Binding': 'ported.lks_utils.input.binding',
    'GestureKind': 'ported.lks_utils.input.binding',
    'InputBindings': 'ported.lks_utils.input.bindings_registry',
    'KeyBinding': 'ported.lks_utils.input.binding',
    'MouseBinding': 'ported.lks_utils.input.binding',
    'MouseButton': 'ported.lks_utils.input.binding',
    'WheelBinding': 'ported.lks_utils.input.binding',
    'get_default_bindings': 'ported.lks_utils.input.bindings_registry',
    'load_per_app_overrides': 'ported.lks_utils.input.per_app_override',
    'save_per_app_overrides': 'ported.lks_utils.input.per_app_override',
}

__all__ = ['Action', 'Binding', 'GestureKind', 'InputBindings', 'KeyBinding', 'MouseBinding', 'MouseButton', 'WheelBinding', 'get_default_bindings', 'load_per_app_overrides', 'save_per_app_overrides']

def __getattr__(name: str) -> Any:
    mod_path = _LAZY_EXPORTS.get(name)
    if mod_path is None:
        raise AttributeError(f"module 'ported.lks_utils.input' "
            f"has no attribute {name!r}")
    mod = importlib.import_module(mod_path)
    value = getattr(mod, name)
    globals()[name] = value
    return value
