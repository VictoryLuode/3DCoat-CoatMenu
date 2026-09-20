"""
Radial menu data model and main exports.

Use this module to access radial menu functionality:
    from ported.utils.ui.widgets.radial_menu import RadialMenuItem, RadialMenuWidget
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

# =============================================================================
# DATA MODEL
# =============================================================================


@dataclass
class RadialMenuItem:
    """Single item in a radial menu."""
    label: str
    action: Callable[[], None]
    icon: str | None = None
    children: list[RadialMenuItem] | None = None
    angle: float | None = None  # Optional explicit angle (0° = up, clockwise)

    @property
    def is_branch(self) -> bool:
        """Return True if this node has children (branch node)."""
        return self.children is not None and len(self.children) > 0

    @property
    def is_leaf(self) -> bool:
        """Return True if this node has no children (leaf node)."""
        return not self.is_branch


# =============================================================================
# IMPORTS (Import widget after data model to avoid circular imports)
# =============================================================================

try:
    from .radial_menu_widget import RadialMenuWidget
    __all__ = ["RadialMenuItem", "RadialMenuWidget"]
except ImportError:
    # PySide6 not available or widget not yet created
    __all__ = ["RadialMenuItem"]
