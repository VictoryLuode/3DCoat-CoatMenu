"""SideRibbon — backed by ported.lks_utils QCollapsiblePanel.

This module provides backward-compatible ``SideRibbon`` and ``Side``
classes that wrap the ported.lks_utils ``QCollapsiblePanel`` internally.

Key changes from the original 3DCoat implementation:
- Content is hidden on collapse (not destroyed) — avoids a crash when the
  tree widget's QProxyStyle is torn down during deferred deletion. The
  per-frame refresh already guards on ``is_expanded``, so the hidden widget
  does not cause idle polling.
- Animation is disabled — window resize fights with animated transitions
- Uses QCollapsiblePanel with ``animated=False`` for instant toggle
- Side enum still works; mapped to ported.lks_utils string directions
- resize_requested signal preserved for collapsed-state drag
- Attention API: pulse + sticky tint on ribbon *text* while collapsed
"""
from __future__ import annotations

from enum import Enum
from typing import Callable

from ported.lks_utils.gui_qt.widgets.collapsible_panel import QCollapsiblePanel

try:
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import (
        Signal,
        QEasingCurve,
        QSequentialAnimationGroup,
        QVariantAnimation,
    )
    from PySide6.QtGui import QColor
    HAS_QT: bool = True
except ImportError:
    HAS_QT = False

from ported.utils.ui.styles import COLOR_ACCENT

# =============================================================================
# CONSTANTS
# =============================================================================

COLLAPSED_WIDTH: int = 28
DEFAULT_EXPANDED_WIDTH: int = 280

# Attention pulse: rise to accent text, settle to sticky unread blend
_ATTENTION_STICKY_STRENGTH: float = 0.55
_ATTENTION_RISE_MS: int = 120
_ATTENTION_FALL_MS: int = 280


def _blend_color(base: QColor, accent: QColor, strength: float) -> QColor:
    """Linear RGB blend from base toward accent (strength in [0, 1])."""
    t: float = max(0.0, min(1.0, strength))
    return QColor(
        int(base.red() + (accent.red() - base.red()) * t),
        int(base.green() + (accent.green() - base.green()) * t),
        int(base.blue() + (accent.blue() - base.blue()) * t),
    )

# =============================================================================
# SIDE ENUM (backward compat)
# =============================================================================

class Side(Enum):
    """Which side of the panel the ribbon attaches to."""
    LEFT = "left"
    RIGHT = "right"


_SIDE_MAP: dict[Side, str] = {
    Side.LEFT: "left",   # content expands left (outward, toward window edge)
    Side.RIGHT: "right", # content expands right (outward, toward window edge)
}

if HAS_QT:

    class SideRibbon(QCollapsiblePanel):
        """A collapsible side ribbon backed by ported.lks_utils QCollapsiblePanel.

        Collapsed: thin vertical bar with anticlockwise-rotated label.
        Expanded: bar + content area with widget created via factory.

        Differences from the original SideRibbon:
        - Content is hidden on collapse (not destroyed) — avoids a crash when
          the tree widget's QProxyStyle is torn down; per-frame refresh already
          guards on ``is_expanded``, so no idle polling occurs.
        - Animation is disabled (``animated=False``) — window resize fights with
          animated transitions, so content appears/disappears instantly
        - The _LogProxy pattern in ui_main.py is still used for safety

        Emits ``toggled`` and ``resize_requested`` for backward compat.
        """

        resize_requested = Signal(int)

        def __init__(
            self,
            edge: Side,
            label: str,
            content_factory: Callable[[], QWidget],
            on_toggled: Callable[[], None] | None = None,
            expanded_width: int = DEFAULT_EXPANDED_WIDTH,
            parent: QWidget | None = None,
        ) -> None:
            direction: str = _SIDE_MAP.get(edge, "right")

            super().__init__(
                parent=parent,
                title=label,
                expand_direction=direction,
                initially_expanded=False,
                content_width=expanded_width,
                animated=False,  # Window resize fights with animation
            )

            self._edge: Side = edge
            self._label: str = label
            self._content_factory: Callable[[], QWidget] = content_factory
            self._on_toggled: Callable[[], None] | None = on_toggled
            self._expanded_width: int = expanded_width
            self._content_widget: QWidget | None = None
            self._content_built: bool = False

            # Attention state (collapsed unread indicator — text only)
            self._attention_active: bool = False
            self._attention_base_color: QColor = self._ribbon.text_color()
            self._attention_anim: QSequentialAnimationGroup | None = None

            # Re-route ribbon clicks through expand/collapse so content
            # is rebuilt by expand() before the panel animates open.
            self._ribbon.clicked.disconnect()
            self._ribbon.clicked.connect(self._on_ribbon_clicked)

            # Wire up toggle callback
            self.toggled.connect(self._handle_toggled)

        # -----------------------------------------------------------------
        # Internal — ribbon click handler
        # -----------------------------------------------------------------

        def _on_ribbon_clicked(self) -> None:
            """Route ribbon clicks through expand/collapse to show/hide content."""
            if self.is_expanded:
                self.collapse()
            else:
                self.expand()

        # -----------------------------------------------------------------
        # Public API (backward compat)
        # -----------------------------------------------------------------

        def toggle(self) -> None:
            """Toggle between collapsed and expanded states."""
            if self.is_expanded:
                self.collapse()
            else:
                self.expand()

        def expand(self) -> None:
            """Expand the ribbon to show content, building if needed."""
            if self.is_expanded:
                return

            if not self._content_built or self._content_widget is None:
                self._content_widget = self._content_factory()
                self.content_layout.addWidget(self._content_widget)
                self._content_built = True
            else:
                # Content exists but is hidden from a previous collapse
                self._content_widget.show()

            self.clear_attention()
            super().expand()

        def collapse(self) -> None:
            """Collapse the ribbon to the thin bar, hiding (not destroying) content."""
            if not self.is_expanded:
                return

            # Hide content BEFORE collapsing (super().collapse triggers window
            # resize which triggers layout/paint).  We do NOT destroy the widget
            # because the tree inside it has a QProxyStyle that crashes 3DCoat
            # during deferred deletion (Qt style chain teardown on deleteLater).
            # _do_refresh_tree() already guards on is_expanded, so keeping the
            # hidden widget alive doesn't cause idle polling.
            if self._content_widget is not None:
                self._content_widget.hide()

            super().collapse()

        def content_widget(self) -> QWidget | None:
            """Return the current content widget, or None if not yet built."""
            return self._content_widget

        def total_width(self) -> int:
            """Return the current total width (collapsed or expanded)."""
            if self.is_expanded:
                ribbon_w: int = 22  # _STRIP_WIDTH from QCollapsiblePanel
                return ribbon_w + self._expanded_width
            return 22  # just the ribbon

        # -----------------------------------------------------------------
        # Attention API (collapsed unread indicator)
        # -----------------------------------------------------------------

        @property
        def has_attention(self) -> bool:
            """True while a sticky unread text tint is active on the ribbon."""
            return self._attention_active

        def signal_attention(self) -> None:
            """Pulse the ribbon *label* if collapsed; settle to a sticky tint.

            Background, border, and arrow stay unchanged — only title text
            color flashes. No-op while expanded. Each call restarts the pulse
            so successive messages remain noticeable without forcing expansion.
            """
            if self.is_expanded:
                return

            self._attention_active = True
            self._restart_attention_pulse()

        def clear_attention(self) -> None:
            """Remove attention text tint/pulse (call when the user expands)."""
            if self._attention_anim is not None:
                self._attention_anim.stop()
                self._attention_anim.deleteLater()
                self._attention_anim = None

            self._ribbon.reset_text_color()
            self._attention_active = False

        def _attention_peak_color(self) -> QColor:
            """Full-accent text color used at pulse peak."""
            return QColor(COLOR_ACCENT)

        def _attention_sticky_color(self) -> QColor:
            """Settled unread text color (softer than peak)."""
            return _blend_color(
                self._attention_base_color,
                self._attention_peak_color(),
                _ATTENTION_STICKY_STRENGTH,
            )

        def _set_attention_text_color(self, color: object) -> None:
            """Apply an interpolated color from the attention animation."""
            if isinstance(color, QColor):
                self._ribbon.set_text_color(color)

        def _restart_attention_pulse(self) -> None:
            """Animate title text: current → peak accent → sticky unread."""
            if self._attention_anim is not None:
                self._attention_anim.stop()
                self._attention_anim.deleteLater()
                self._attention_anim = None

            start_color: QColor = self._ribbon.text_color()
            peak_color: QColor = self._attention_peak_color()
            sticky_color: QColor = self._attention_sticky_color()
            group: QSequentialAnimationGroup = QSequentialAnimationGroup(self)

            rise: QVariantAnimation = QVariantAnimation(self)
            rise.setDuration(_ATTENTION_RISE_MS)
            rise.setStartValue(start_color)
            rise.setEndValue(peak_color)
            rise.setEasingCurve(QEasingCurve.Type.OutQuad)
            rise.valueChanged.connect(self._set_attention_text_color)

            fall: QVariantAnimation = QVariantAnimation(self)
            fall.setDuration(_ATTENTION_FALL_MS)
            fall.setStartValue(peak_color)
            fall.setEndValue(sticky_color)
            fall.setEasingCurve(QEasingCurve.Type.InOutQuad)
            fall.valueChanged.connect(self._set_attention_text_color)

            group.addAnimation(rise)
            group.addAnimation(fall)
            self._attention_anim = group
            group.start()

        # -----------------------------------------------------------------
        # Internal
        # -----------------------------------------------------------------

        def _handle_toggled(self, expanded: bool) -> None:
            """Handle toggle: clear attention on expand; call on_toggled."""
            if expanded:
                self.clear_attention()
            if self._on_toggled:
                self._on_toggled()

else:
    # Stubs when PySide6 is not available
    class Side(Enum):  # type: ignore[no-redef]
        LEFT = "left"
        RIGHT = "right"

    class SideRibbon:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            pass
        def toggle(self) -> None: pass
        def expand(self) -> None: pass
        def collapse(self) -> None: pass
        @property
        def is_expanded(self) -> bool: return False
        def content_widget(self) -> None: return None
        def total_width(self) -> int: return 0
        @property
        def has_attention(self) -> bool: return False
        def signal_attention(self) -> None: pass
        def clear_attention(self) -> None: pass


__all__ = ["SideRibbon", "Side"]
