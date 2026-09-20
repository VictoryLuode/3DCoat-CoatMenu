"""CollapsibleSection — 3DCoat-styled wrapper around ported.lks_utils QCollapsibleSection.

Provides the 3DCoat look: rounded container frame, SVG icon badge in header,
accent-colored text, and left accent line on content area.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QScrollArea, QSizePolicy
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QResizeEvent

    HAS_QT: bool = True
except ImportError:
    HAS_QT = False

from ported.lks_utils.gui_qt.widgets.collapsible_section import QCollapsibleSection as _QCollapsibleSection

if HAS_QT:
    import sys

    # =========================================================================
    # STATE PERSISTENCE HOOKS — wire into 3DCoat's lks_settings
    # =========================================================================

    def _lks_state_loader(state_key: str) -> bool | None:
        """Load collapsed state from lks_settings."""
        try:
            from ported.utils.lks_settings import get_ui_state
            ui_state = get_ui_state()
            expanded = getattr(ui_state, f"{state_key}_expanded", None)
            if expanded is not None:
                return expanded
        except Exception:
            pass
        return None

    def _lks_state_saver(state_key: str, expanded: bool) -> None:
        """Save collapsed state to lks_settings."""
        try:
            from ported.utils.lks_settings import get_ui_state, save_ui_state
            ui_state = get_ui_state()
            setattr(ui_state, f"{state_key}_expanded", expanded)
            save_ui_state()
        except Exception:
            pass

    # Install hooks on the ported.lks_utils class (only once)
    if _QCollapsibleSection._state_loader is None:
        _QCollapsibleSection._state_loader = _lks_state_loader
    if _QCollapsibleSection._state_saver is None:
        _QCollapsibleSection._state_saver = _lks_state_saver

    # =========================================================================
    # 3DCOAT-STYLED COLLAPSIBLE SECTION
    # =========================================================================

    class CollapsibleSection(QFrame):
        """3DCoat-styled collapsible section with SVG icon and themed formatting.

        Wraps ported.lks_utils ``QCollapsibleSection`` inside a rounded container
        frame with accent-colored header text and left accent line on the
        content area.  SVG icons are loaded from
        ``ported.utils/ui/data/<name>.svg``.
        """

        toggled = Signal(bool)
        enabled_changed = Signal(bool)

        def __init__(
            self,
            parent: QWidget | None = None,
            title: str = "Section",
            collapsed: bool = False,
            checkable: bool = False,
            checked: bool = True,
            color: str = "#90caf9",
            state_key: str | None = None,
            icon_name: str | None = None,
            help_text: str | None = None,
        ) -> None:
            super().__init__(parent)

            # Use Maximum vertical so sections hug their content and never
            # stretch to fill extra space. Expanding horizontal so they
            # fill available width.
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

            # Rounded container frame styling
            self.setStyleSheet("""
                CollapsibleSection {
                    background-color: #2b2b2b;
                    border: 1px solid #3a3a3a;
                    border-radius: 6px;
                }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            # Build SVG icon badge from icon_name (passed ``color`` used
            # for both the icon and the accent line).
            badge: QWidget | None = None
            if icon_name is not None:
                from .svg_icon import SvgIcon
                icon_color: str = color
                badge = SvgIcon(name=icon_name, size=24, min_size=20, color=icon_color)

            # Create inner ported.lks_utils section.
            # Do NOT pass icon_name — prevents text duplication; the icon
            # is handled as badge_widget instead.
            self._section = _QCollapsibleSection(
                title=title,
                parent=self,
                has_checkbox=checkable,
                initially_expanded=not collapsed,
                initially_enabled=checked,
                fill_vertical=False,
                state_key=state_key,
                icon_name=None,
                badge_widget=badge,
                bar_height=26,
                header_font_size=10,
            )
            self._section.toggled.connect(self.toggled.emit)
            self._section.enabled_changed.connect(self.enabled_changed.emit)

            # Override inner section's size policy to Maximum — the
            # ported.lks_utils default is Maximum, ensuring content hugs tightly.
            self._section.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            if hasattr(self._section, "_scroll"):
                self._section._scroll.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

            layout.addWidget(self._section)

            # Info button overlay — positioned at top-right of the header
            # ribbon using absolute positioning. Lives as a child of this
            # QFrame so it floats above the inner section.
            self._info_button: QWidget | None = None
            if help_text is not None and help_text.strip():
                from .info_button import InfoButtonCompact
                self._info_button = InfoButtonCompact(
                    help_text=help_text, parent=self)
                self._info_button.show()
                self._info_button.raise_()  # ensure above inner section

                # #region agent log
                import time as _time3, json as _json3
                _parent_chain2: list[str] = []
                _w2 = self._info_button
                for _ in range(5):
                    _p2 = _w2.parentWidget()
                    if _p2 is None:
                        break
                    _ss2 = _p2.styleSheet()
                    _parent_chain2.append(f"{_p2.__class__.__name__}(ss_len={len(_ss2)})")
                    _w2 = _p2
                _log_payload = {
                    "sessionId": "d2fb9f",
                    "runId": "initial",
                    "hypothesisId": "H1",
                    "location": "collapsible_section.py:147",
                    "message": "info_button_in_collapsible_section",
                    "data": {
                        "objectName": self._info_button.objectName(),
                        "isFlat": self._info_button.isFlat(),
                        "geometry": {"w": self._info_button.width(), "h": self._info_button.height()},
                        "sizePolicy": str(self._info_button.sizePolicy()),
                        "parentChain": _parent_chain2,
                        "selfStyleSheetLen": len(self._info_button.styleSheet()),
                    },
                    "timestamp": _time3.time() * 1000,
                }
                try:
                    with open("debug-d2fb9f.log", "a", encoding="utf-8") as _f:
                        _f.write(_json3.dumps(_log_payload) + "\n")
                except Exception:
                    pass
                # #endregion

            # Left accent line on content area only (not children)
            self._section.content.setObjectName("_lks_content")
            self._section.content.setStyleSheet("""
                QWidget#_lks_content {
                    border-left: 2px solid #90caf9;
                    background: transparent;
                }
                QWidget#_lks_content QWidget {
                    border-left: 0px;
                }
            """)

            self._checkable: bool = checkable
            self._checked: bool = checked

        # -----------------------------------------------------------------
        # resizeEvent — keep info button pinned to top-right
        # -----------------------------------------------------------------

        def resizeEvent(self, event: QResizeEvent) -> None:
            super().resizeEvent(event)
            self._reposition_info_button()

        def _reposition_info_button(self) -> None:
            """Pin the info button to the top-right of the header ribbon."""
            if self._info_button is None:
                return
            btn_size: int = self._info_button.width()
            # Vertically centered in the 26px header bar
            y: int = (26 - btn_size) // 2
            x: int = self.width() - btn_size - 6  # 6px from right edge
            self._info_button.move(x, y)

        # -----------------------------------------------------------------
        # Delegated properties
        # -----------------------------------------------------------------

        @property
        def content(self) -> QWidget:
            return self._section.content

        @property
        def content_layout(self) -> QVBoxLayout:
            return self._section.content_layout

        @property
        def is_expanded(self) -> bool:
            return self._section.is_expanded

        # -----------------------------------------------------------------
        # API compat
        # -----------------------------------------------------------------

        def is_collapsed(self) -> bool:
            return not self._section.is_expanded

        def is_enabled(self) -> bool:
            result = self._section.is_enabled
            return True if result is None else result

        def expand(self) -> None:
            self._section.expand()

        def collapse(self) -> None:
            self._section.collapse()

        def set_enabled(self, enabled: bool) -> None:
            if self._checkable:
                self._section.set_enabled(enabled)

        def set_title(self, title: str) -> None:
            self._section._header.set_title(title)

        def set_content_visible(self, visible: bool) -> None:
            if visible:
                self._section.expand()
            else:
                self._section.collapse()

        def schedule_geometry_sync(self) -> None:
            self._section.schedule_geometry_sync()

else:
    # Stub class when PySide6 is not available
    class CollapsibleSection:  # type: ignore[no-redef]
        """Stub CollapsibleSection for when Qt is not available."""

        toggled = None
        enabled_changed = None

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        @property
        def content(self):
            return None

        @property
        def content_layout(self):
            return None

        @property
        def is_expanded(self) -> bool:
            return True

        def is_collapsed(self) -> bool:
            return False

        def is_enabled(self) -> bool:
            return True

        def expand(self) -> None:
            pass

        def collapse(self) -> None:
            pass

        def set_enabled(self, enabled: bool) -> None:
            pass

        def set_title(self, title: str) -> None:
            pass

        def set_content_visible(self, visible: bool) -> None:
            pass

        def schedule_geometry_sync(self) -> None:
            pass


__all__ = ["CollapsibleSection"]
