"""ButtonGrid — re-exported from ported.lks_utils with add_scope_buttons extension."""
from __future__ import annotations
from typing import Callable

from ported.lks_utils.gui_qt.widgets.button_grid import QButtonGrid as _QButtonGrid
from PySide6.QtWidgets import QPushButton


class ButtonGrid(_QButtonGrid):
    """ButtonGrid extended with add_scope_buttons convenience method.

    Delegates all base functionality to ported.lks_utils QButtonGrid and adds
    the 3DCoat-specific scope-button helper.
    """

    def add_scope_buttons(
        self,
        on_current: Callable[[], None],
        on_tree: Callable[[], None],
        on_all: Callable[[], None],
        current_tooltip: str = "Apply to selected",
        tree_tooltip: str = "Apply to subtree",
        all_tooltip: str = "Apply to all",
    ) -> tuple[QPushButton, QPushButton, QPushButton]:
        """Add three scope buttons using SvgIconButton.

        Returns:
            Tuple of (selected_btn, subtree_btn, all_btn).
        """
        from .svg_icon import SvgIconButton

        btn_sel = SvgIconButton("scope_selected", size=24, tooltip=current_tooltip)
        btn_tree = SvgIconButton("scope_subtree", size=24, tooltip=tree_tooltip)
        btn_all = SvgIconButton("scope_all", size=24, tooltip=all_tooltip)

        btn_sel.clicked.connect(on_current)
        btn_tree.clicked.connect(on_tree)
        btn_all.clicked.connect(on_all)

        self.add_widget(btn_sel)
        self.add_widget(btn_tree)
        self.add_widget(btn_all)

        self._buttons.append(btn_sel)
        self._buttons.append(btn_tree)
        self._buttons.append(btn_all)

        return btn_sel, btn_tree, btn_all


__all__ = ["ButtonGrid"]
