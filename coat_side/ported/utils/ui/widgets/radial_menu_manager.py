"""
Radial Menu Manager - Singleton managing radial menu lifecycle.

Provides a high-level interface for showing radial menus at cursor position,
loading menu configuration, and handling menu events.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .radial_menu import RadialMenuItem

try:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QCursor
    HAS_QT = True
except ImportError:
    HAS_QT = False


# =============================================================================
# LOGGING HELPER
# =============================================================================

def _log_manager(message: str) -> None:
    """Log a radial menu manager event to the InvocationLogger and console."""
    print(f"[RadialMenuManager] {message}")
    try:
        from ported.utils.invocation_logger import get_invocation_logger
        logger = get_invocation_logger()
        logger.log_debug(f"[RadialMenuManager] {message}")
    except ImportError:
        pass


# =============================================================================
# MANAGER CLASS
# =============================================================================

class RadialMenuManager:
    """
    Singleton managing radial menu widget lifecycle.

    Responsibilities:
    - Create and own RadialMenuWidget instance
    - Show menu at cursor position with given items
    - Load menu configuration from settings/config
    - Handle menu close and action invocation

    Usage:
        manager = get_manager()
        manager.show_menu(items)  # Show at cursor position
    """
    _instance: RadialMenuManager | None = None

    def __init__(self):
        """Initialize manager (use get_manager() instead)."""
        if not HAS_QT:
            raise ImportError("PySide6 required for RadialMenuManager")

        # Import here to avoid circular dependency
        from .radial_menu import RadialMenuWidget

        self._widget: RadialMenuWidget = RadialMenuWidget()
        self._current_items: list[RadialMenuItem] = []
        self._trigger_keycode: int | None = None  # Qt keycode for the trigger key

    def show_menu(
        self,
        items: list[RadialMenuItem],
        pos: QPoint | None = None,
        action_id: str | None = None,
        script_path: str | None = None,
        menu_radius: int | None = None,
        **kwargs: object,
    ) -> None:
        """
        Show radial menu at specified position (or cursor if None).

        Args:
            items: List of menu items to display
            pos: Position to show menu at (None = cursor position)
            action_id: 3DCoat action/menu identifier that launched this menu
            script_path: Absolute path to the launching action script (optional).
                Used to also match ``execute:<path>`` hotkey IDs that 3DCoat
                creates when the script is bound from the Scripts browser.
            menu_radius: Fixed pie radius in pixels (overrides global setting).
        """
        # CRITICAL: If menu is already visible, directly update the existing widget
        # instead of hide→processEvents→show_at, which causes a visible flicker gap.
        if self._widget.isVisible():
            self._current_items = items

            # Query hotkey for the trigger key
            self._trigger_keycode = self._query_trigger_key(
                action_id, script_path=script_path)

            # Load settings from lks_settings
            self._load_settings()
            if menu_radius is not None:
                self._widget.set_geometry_params(menu_radius=int(menu_radius))

            # Set items on widget
            self._widget.set_items(items)

            # Set menu name for center label
            menu_name: str = str(kwargs.pop("menu_name", "") or "")
            self._widget.set_menu_name(menu_name)

            # Pass trigger keycode to widget
            self._widget.set_trigger_keycode(self._trigger_keycode)

            # Restart appear animation without hide/show cycle
            import time as _time
            self._widget._anim_start_time = _time.monotonic()
            self._widget._anim_active = True
            self._widget.update()
            return

        if not items:
            return

        # Store current items
        self._current_items = items

        # Query hotkey for the trigger key
        self._trigger_keycode = self._query_trigger_key(
            action_id, script_path=script_path)

        # Load settings from lks_settings
        self._load_settings()
        if menu_radius is not None:
            self._widget.set_geometry_params(menu_radius=int(menu_radius))

        # Set items on widget
        self._widget.set_items(items)

        # Set menu name for center label
        menu_name = str(kwargs.pop("menu_name", "") or "")
        self._widget.set_menu_name(menu_name)

        # Pass trigger keycode to widget
        self._widget.set_trigger_keycode(self._trigger_keycode)

        # Show at cursor position if not specified
        if pos is None:
            pos = QCursor.pos()

        self._widget.show_at(pos)

    def hide_menu(self) -> None:
        """Hide the menu without invoking action.

        Fully tears down polling, fade animations, and opacity so a cancelled
        preview / Escape path cannot leave an invisible always-on-top ToolTip
        overlay that blocks mouse and keyboard to the LKS panel.
        """
        widget = self._widget
        if hasattr(widget, "dismiss_without_invoke"):
            widget.dismiss_without_invoke()
            return
        if hasattr(widget, "_cursor_poll_timer"):
            widget._cursor_poll_timer.stop()
        widget.hide()

    def _query_trigger_key(
        self,
        action_id: str | None = None,
        script_path: str | None = None,
    ) -> int | None:
        """Query hotkeys file to find which key is mapped to this action.

        3DCoat often stores TWO hotkey IDs for the same radial script:
        - The registered menu id (e.g. ``LKS_Radial_LksRadialV1``)
        - An ``execute:<absolute-script-path>`` id from the Scripts browser

        Those can be bound to *different* keys. Prefer the binding that is
        currently held. Never fall back to a non-held key when multiple
        distinct keys are candidates — that falsely enables flick mode and
        closes the menu in ~120ms ("bounce").

        When both ``action_id`` and ``script_path`` are omitted (editor
        preview / programmatic show), return ``None`` — do **not** invent
        ``LKS_RadialMenu_Show``. That fallback falsely arms flick-close and
        synthetic key-up for whatever hotkey that id has bound, which can
        steal/leave panel keyboard focus permanently broken.
        """
        try:
            from pathlib import Path

            from ported.utils.hotkey_utils import HotkeyEntry, parse_hotkeys_file, get_default_hotkeys_path
            from ported.utils.keycode_map import coat_to_qt_key
            from ported.utils.win32_key_state import binding_is_active

            # Preview / bare show_menu(items): no launching action → no trigger.
            if action_id is None and not script_path:
                return None

            resolved_action_id: str | None = action_id

            # Get hotkeys path
            hotkeys_path = get_default_hotkeys_path()
            if not hotkeys_path or not hotkeys_path.exists():
                return None

            hotkeys_file = parse_hotkeys_file(hotkeys_path)

            candidates: list[tuple[HotkeyEntry, int]] = []
            action_variants: set[str] = set()
            if resolved_action_id is not None:
                action_variants.add(resolved_action_id)
                action_variants.add(f"${resolved_action_id}")
                if resolved_action_id.startswith("$"):
                    action_variants.add(resolved_action_id[1:])

            # Script basenames that identify execute:<path> hotkey IDs
            script_basenames: set[str] = set()
            if script_path:
                script_basenames.add(Path(script_path).name.lower())
            # Derive from menu action id: LKS_Radial_Foo → LKS_RadialMenu_Foo.py
            if resolved_action_id is not None:
                if resolved_action_id.startswith("LKS_Radial_"):
                    suffix: str = resolved_action_id[len("LKS_Radial_"):]
                    script_basenames.add(f"LKS_RadialMenu_{suffix}.py".lower())
                elif resolved_action_id == "LKS_RadialMenu_Show":
                    script_basenames.add("lks_radialmenu_show.py")

            def _matches_execute_id(entry_id: str) -> bool:
                if not entry_id.startswith("execute:"):
                    return False
                if not script_basenames:
                    return False
                # Normalize slashes then compare basename
                normalized: str = entry_id.replace("\\", "/")
                basename: str = normalized.rsplit("/", 1)[-1].lower()
                return basename in script_basenames

            for entry in hotkeys_file.entries:
                if not entry.is_assigned:
                    continue
                if entry.id not in action_variants and not _matches_execute_id(entry.id):
                    continue

                qt_key = coat_to_qt_key(entry.code)
                if qt_key is not None:
                    candidates.append((entry, qt_key))

            if not candidates:
                return None

            active_candidates: list[int] = []
            for entry, qt_key in candidates:
                if binding_is_active(
                    qt_key,
                    ctrl=entry.ctrl,
                    alt=entry.alt,
                    shift=entry.shift,
                ):
                    active_candidates.append(qt_key)

            label: str = resolved_action_id or (script_path or "unknown")

            unique_active: list[int] = list(dict.fromkeys(active_candidates))
            if len(unique_active) == 1:
                return unique_active[0]
            if len(unique_active) > 1:
                _log_manager(
                    f"Ambiguous active bindings for {label}: "
                    f"{len(unique_active)} candidates"
                )
                return unique_active[0]

            # Nothing currently held — flick-mode fallback.
            unique_candidates: list[int] = list(
                dict.fromkeys(qt_key for _, qt_key in candidates))
            if len(unique_candidates) == 1:
                # Same physical key across all matching IDs (menu id + execute:
                # duplicate). Safe to treat as a flick of that key.
                return unique_candidates[0]

            # Distinct keys bound to the same script (e.g. Shift+B on menu id
            # and Alt+~ on execute:path). Guessing either one enables flick
            # mode for a key the user did not press → menu bounce-closes.
            _log_manager(
                f"Ambiguous bindings for {label}: "
                f"{len(unique_candidates)} distinct keys and none currently held "
                f"— skipping flick fallback to avoid bounce-close"
            )
            return None
        except Exception as e:
            _log_manager(f"Failed to query trigger key: {e}")
            return None

    def _load_settings(self) -> None:
        """Load radial menu settings from lks_settings."""
        try:
            from ported.utils.lks_settings import get_settings
            settings = get_settings()

            # Update widget constants from settings
            from .radial_menu import (
                DEAD_ZONE_RADIUS, MENU_RADIUS,
                BRANCH_HOVER_RADIUS, BRANCH_DWELL_MS
            )

            # Read settings (with fallback to current constants)
            dead_zone = settings.get(
                "radial_menu_dead_zone_radius", DEAD_ZONE_RADIUS)
            menu_radius = settings.get("radial_menu_menu_radius", MENU_RADIUS)
            branch_hover = settings.get(
                "radial_menu_branch_hover_radius", BRANCH_HOVER_RADIUS)
            branch_dwell = settings.get(
                "radial_menu_branch_dwell_ms", BRANCH_DWELL_MS)

            # Apply to widget
            self._widget.set_geometry_params(
                dead_zone_radius=dead_zone,
                menu_radius=menu_radius,
                branch_hover_radius=branch_hover,
                branch_dwell_ms=branch_dwell,
            )
        except ImportError:
            # lks_settings not available (standalone mode)
            _log_manager("lks_settings not available, using defaults")
        except Exception as e:
            _log_manager(f"Failed to load settings: {e}")


# =============================================================================
# MODULE-LEVEL ACCESSOR
# =============================================================================

def get_manager() -> RadialMenuManager:
    """Get or create the singleton RadialMenuManager instance."""
    if RadialMenuManager._instance is None:
        RadialMenuManager._instance = RadialMenuManager()
    return RadialMenuManager._instance
