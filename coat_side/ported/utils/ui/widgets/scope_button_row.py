"""
ScopeButtonRow widget — a fixed 3-slot row of scope buttons (Sel/Tree/All).

Each scope occupies a fixed-size 24×24 slot. Hidden scopes reserve their
space so all ScopeButtonRow instances in a GridRowTable stay column-aligned.

Usage:
    from ported.utils.ui.widgets.scope_button_row import ScopeButtonRow

    row = ScopeButtonRow()
    row.set_callback("sel", lambda: do_thing("CURRENT"))
    row.set_callback("tree", lambda: do_thing("TREE"))
    row.set_callback("all", lambda: do_thing("ALL"))
    row.set_tooltips(sel="Apply to selected", tree="Apply to subtree")

    # Hide a scope (reserves space):
    row.set_callback("sel", None)

    # Place in a GridRowTable cell or any layout:
    table.add_cell(0, 1, row)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

try:
    from PySide6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy

    HAS_QT: bool = True
except ImportError:
    HAS_QT = False

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget as QWidgetType


# =============================================================================
# SCOPE BUTTON ROW (HAS_QT)
# =============================================================================

if HAS_QT:

    def _create_scope_button(icon_name: str) -> object:
        """Create an SvgIconButton for a scope slot (Qt-only helper)."""
        from .svg_icon import SvgIconButton
        return SvgIconButton(icon_name, size=24, tooltip=None)

    class ScopeButtonRow(QWidget):
        """
        Fixed 3-slot row of scope buttons: Sel, Tree, All.

        Hidden scopes reserve their 24×24 layout space so vertical
        alignment is preserved across rows in GridRowTable.

        Args:
            parent: Optional parent widget
        """

        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__(parent)

            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            self._callbacks: dict[str, Callable[[], None] | None] = {
                "sel": None,
                "tree": None,
                "all": None,
            }

            layout: QHBoxLayout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)

            # ── helpers ──────────────────────────────────────────────
            def _make_slot() -> tuple[QWidget, QHBoxLayout]:
                wrapper: QWidget = QWidget()
                wrapper.setFixedSize(24, 24)
                wrapper.setStyleSheet("background: transparent;")
                wl: QHBoxLayout = QHBoxLayout(wrapper)
                wl.setContentsMargins(0, 0, 0, 0)
                wl.setSpacing(0)
                return wrapper, wl

            # ── Sel slot ─────────────────────────────────────────────
            self._wrap_sel, sel_layout = _make_slot()
            self._btn_sel = _create_scope_button("scope_selected")
            sel_layout.addWidget(self._btn_sel)
            layout.addWidget(self._wrap_sel)

            # ── Tree slot ────────────────────────────────────────────
            self._wrap_tree, tree_layout = _make_slot()
            self._btn_tree = _create_scope_button("scope_subtree")
            tree_layout.addWidget(self._btn_tree)
            layout.addWidget(self._wrap_tree)

            # ── All slot ─────────────────────────────────────────────
            self._wrap_all, all_layout = _make_slot()
            self._btn_all = _create_scope_button("scope_all")
            all_layout.addWidget(self._btn_all)
            layout.addWidget(self._wrap_all)

        # -----------------------------------------------------------------
        # Public API
        # -----------------------------------------------------------------

        def set_callback(
            self,
            scope: str,
            callback: Callable[[], None] | None,
        ) -> None:
            """
            Set or clear the callback for a scope slot.

            Passing ``None`` hides the button while keeping its 24×24
            wrapper visible so column alignment is preserved.

            Args:
                scope: One of ``"sel"``, ``"tree"``, ``"all"``
                callback: Click handler, or None to hide the slot
            """
            if scope not in self._callbacks:
                raise ValueError(
                    f"Unknown scope '{scope}'. Use 'sel', 'tree', or 'all'."
                )

            btn: QWidget = getattr(self, f"_btn_{scope}")

            # Disconnect any previous connection
            import warnings
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    btn.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass

            self._callbacks[scope] = callback

            if callback is None:
                btn.hide()
            else:
                btn.clicked.connect(callback)
                btn.show()

        def set_tooltips(
            self,
            sel: str | None = None,
            tree: str | None = None,
            all: str | None = None,
        ) -> None:
            """
            Set tooltip text for scope buttons.

            Args:
                sel: Tooltip for the Sel button
                tree: Tooltip for the Tree button
                all: Tooltip for the All button
            """
            if sel is not None:
                self._btn_sel.setToolTip(sel)
            if tree is not None:
                self._btn_tree.setToolTip(tree)
            if all is not None:
                self._btn_all.setToolTip(all)


else:

    class ScopeButtonRow:  # type: ignore[no-redef]
        """Stub ScopeButtonRow when PySide6 is not available."""

        def __init__(self, parent: object | None = None) -> None:  # noqa: ARG002
            pass

        def set_callback(
            self, scope: str, callback: object | None,
        ) -> None:
            pass

        def set_tooltips(
            self,
            sel: str | None = None,
            tree: str | None = None,
            all: str | None = None,
        ) -> None:
            pass
