"""`InputBindings`: action ↔ binding registry.

The single source of truth for "which event triggers which action" in
the running app. Widgets register actions with default bindings at
import time; the user can override those bindings via the (future)
shortcut editor; bindings are persisted to JSON.

Event resolution is the inverse: given a real Qt event, return the
list of action ids that match. Widgets dispatch from there.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ported.lks_utils.input.action import Action
from ported.lks_utils.input.binding import (
    Binding,
    GestureKind,
    KeyBinding,
    Modifier,
    MouseBinding,
    MouseButton,
    WheelBinding,
)


class _RegisteredAction:
    __slots__ = ("action", "defaults", "current")

    def __init__(self, action: Action, defaults: list[Binding]) -> None:
        self.action = action
        self.defaults: tuple[Binding, ...] = tuple(defaults)
        self.current: tuple[Binding, ...] = tuple(defaults)


class InputBindings:
    """Registry of `Action` → list of `Binding`.

    Typical usage from a widget::

        from ported.lks_utils.input import (
            Action, InputBindings, MouseBinding, MouseButton, GestureKind,
            get_default_bindings,
        )

        STROKE = Action(
            id="painter.brush.stroke",
            label="Paint stroke",
            category="Painter",
        )
        get_default_bindings().register(
            STROKE,
            [MouseBinding(MouseButton.LEFT, gesture=GestureKind.DRAG)],
        )

    At event-handling time the widget asks the registry::

        bindings = get_default_bindings()
        if bindings.matches_mouse(STROKE.id, button, modifiers, gesture):
            ...

    Attributes:
        on_change: Optional callable invoked whenever bindings change
            (used by the future shortcut editor to live-refresh widgets).
    """

    def __init__(self) -> None:
        self._actions: dict[str, _RegisteredAction] = {}
        self.on_change: list = []  # list[callable[[str], None]]

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def register(self, action: Action, defaults: Iterable[Binding]) -> None:
        """Register ``action`` with its default bindings.

        Idempotent: re-registering the same action with the same defaults
        is a no-op (lets multiple widgets safely register at import time).
        Re-registering with *different* defaults raises so we catch
        accidental id collisions early.
        """
        defaults_tuple = tuple(defaults)
        existing = self._actions.get(action.id)
        if existing is not None:
            if existing.action != action or existing.defaults != defaults_tuple:
                raise ValueError(
                    f"Action {action.id!r} already registered with different "
                    f"definition or defaults"
                )
            return
        self._actions[action.id] = _RegisteredAction(
            action, list(defaults_tuple))

    def actions(self) -> list[Action]:
        """All registered actions, sorted by category then label."""
        return sorted(
            (entry.action for entry in self._actions.values()),
            key=lambda a: (a.category, a.label, a.id),
        )

    def get_bindings(self, action_id: str) -> tuple[Binding, ...]:
        """Current bindings for ``action_id`` (defaults if never overridden)."""
        return self._actions[action_id].current

    def get_defaults(self, action_id: str) -> tuple[Binding, ...]:
        return self._actions[action_id].defaults

    def set_bindings(self, action_id: str, bindings: Iterable[Binding]) -> None:
        """Replace bindings for ``action_id`` (the user-override path)."""
        if action_id not in self._actions:
            raise KeyError(f"unknown action: {action_id!r}")
        self._actions[action_id].current = tuple(bindings)
        self._fire_change(action_id)

    def reset(self, action_id: str) -> None:
        """Restore ``action_id`` to its registered defaults."""
        entry = self._actions[action_id]
        entry.current = entry.defaults
        self._fire_change(action_id)

    def reset_all(self) -> None:
        for entry in self._actions.values():
            entry.current = entry.defaults
        self._fire_change("*")

    def all_actions(self) -> list[Action]:
        """All registered actions (alias for `actions()`)."""
        return self.actions()

    # ------------------------------------------------------------------ #
    # Scope and override composition                                       #
    # ------------------------------------------------------------------ #

    def _copy(self) -> InputBindings:
        """Return a deep copy sharing no mutable state with the original."""
        new = InputBindings()
        for action_id, entry in self._actions.items():
            new._actions[action_id] = _RegisteredAction(
                entry.action, list(entry.defaults))
            new._actions[action_id].current = entry.current
        return new

    def with_overrides(
        self,
        *,
        overrides: dict[Action, list[Binding]] | None = None,
        scope: str | None = None,
        scope_overrides: dict[str, dict[Action, list[Binding]]] | None = None,
    ) -> InputBindings:
        """Return a NEW ``InputBindings`` with the given overrides applied.

        The original registry is not modified.

        Args:
            overrides: Per-action override map.  Keys that are not registered
                in this instance are silently ignored.
            scope: Unused here (provided for call-site symmetry; callers
                typically combine ``with_overrides`` + ``for_scope``).
            scope_overrides: dict of ``{scope_str: {Action: [Binding]}}``.
                Overrides are applied only when the action's
                ``Action.scope`` matches the outer key.
        """
        new = self._copy()
        if overrides:
            for action, bindings in overrides.items():
                if action.id in new._actions:
                    new._actions[action.id].current = tuple(bindings)
        if scope_overrides:
            for sc, sc_map in scope_overrides.items():
                for action, bindings in sc_map.items():
                    entry = new._actions.get(action.id)
                    if entry is not None and entry.action.scope == sc:
                        entry.current = tuple(bindings)
        return new

    def for_scope(self, scope: str) -> InputBindings:
        """Return a view that contains only ``"global"`` and ``scope`` actions."""
        new = InputBindings()
        for action_id, entry in self._actions.items():
            if entry.action.scope in ("global", scope):
                new._actions[action_id] = _RegisteredAction(
                    entry.action, list(entry.defaults))
                new._actions[action_id].current = entry.current
        return new

    def validate_no_conflicts(
        self, *, scopes: list[str] | None = None
    ) -> None:
        """Raise ``ValueError`` if two actions in the active scopes share a gesture.

        Args:
            scopes: Active scope names (``"global"`` is always included).
                ``None`` checks the entire registry.
        """
        if scopes is None:
            relevant = list(self._actions.values())
        else:
            active = set(scopes) | {"global"}
            relevant = [e for e in self._actions.values()
                        if e.action.scope in active]

        seen: dict[tuple, str] = {}
        conflicts: list[tuple[str, str, Binding]] = []
        for entry in relevant:
            for b in entry.current:
                key = _binding_key(b)
                if key in seen:
                    conflicts.append((seen[key], entry.action.id, b))
                else:
                    seen[key] = entry.action.id
        if conflicts:
            lines = [f"  {a1!r} vs {a2!r}: {b!r}" for a1, a2, b in conflicts]
            raise ValueError(
                "Binding conflicts detected:\n" + "\n".join(lines))

    # ------------------------------------------------------------------ #
    # Event matching                                                       #
    # ------------------------------------------------------------------ #

    def matches_key(
        self, action_id: str, key_sequence: str
    ) -> bool:
        """True iff ``key_sequence`` (Qt-style, e.g. ``"Ctrl+S"``) is bound."""
        entry = self._actions.get(action_id)
        if entry is None:
            return False
        for b in entry.current:
            if isinstance(b, KeyBinding) and _normalise_key(b.key) == _normalise_key(key_sequence):
                return True
        return False

    def matches_mouse(
        self,
        action_id: str,
        button: MouseButton,
        modifiers: frozenset[Modifier],
        gesture: GestureKind,
    ) -> bool:
        """True iff a `MouseBinding` for this action matches the inputs."""
        entry = self._actions.get(action_id)
        if entry is None:
            return False
        for b in entry.current:
            if (
                isinstance(b, MouseBinding)
                and b.button == button
                and b.modifiers == modifiers
                and b.gesture == gesture
            ):
                return True
        return False

    def matches_wheel(
        self,
        action_id: str,
        modifiers: frozenset[Modifier],
        direction: str,
    ) -> bool:
        """True iff a `WheelBinding` matches. ``direction`` is ``"up"|"down"``."""
        if direction not in {"up", "down"}:
            raise ValueError(
                f"direction must be 'up'|'down', got {direction!r}")
        entry = self._actions.get(action_id)
        if entry is None:
            return False
        for b in entry.current:
            if isinstance(b, WheelBinding) and b.modifiers == modifiers:
                if b.direction == "any" or b.direction == direction:
                    return True
        return False

    def resolve_mouse(
        self,
        button: MouseButton,
        modifiers: frozenset[Modifier],
        gesture: GestureKind,
    ) -> list[str]:
        """All action ids matched by the given mouse triple. Order: deterministic."""
        return sorted(
            action_id
            for action_id, entry in self._actions.items()
            if any(
                isinstance(b, MouseBinding)
                and b.button == button
                and b.modifiers == modifiers
                and b.gesture == gesture
                for b in entry.current
            )
        )

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Serialise *only the overrides* (entries that differ from defaults)."""
        out: dict = {}
        for action_id, entry in self._actions.items():
            if entry.current != entry.defaults:
                out[action_id] = [_binding_to_dict(b) for b in entry.current]
        return {"version": 1, "overrides": out}

    def from_dict(self, data: dict) -> None:
        """Apply overrides from ``data`` produced by `to_dict`."""
        if data.get("version") != 1:
            raise ValueError(
                f"unsupported bindings version: {data.get('version')!r}")
        overrides = data.get("overrides", {})
        for action_id, raw_list in overrides.items():
            if action_id not in self._actions:
                # Skip silently: an old config may reference removed actions.
                continue
            self._actions[action_id].current = tuple(
                _binding_from_dict(d) for d in raw_list
            )
        self._fire_change("*")

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        self.from_dict(json.loads(path.read_text(encoding="utf-8")))

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _fire_change(self, action_id: str) -> None:
        for cb in self.on_change:
            try:
                cb(action_id)
            except Exception:  # noqa: BLE001 — listener errors must not break input
                pass


# Canonical aliases: any variant key name maps to the canonical lowercase form.
# Used so that registering with "Delete" also matches incoming "Del" events
# (and vice versa), "Enter" matches "Return", etc.
_KEY_ALIASES: dict[str, str] = {
    "del": "delete",
    "enter": "return",
    "esc": "escape",
    "ins": "insert",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "prior": "pageup",
    "next": "pagedown",
}


def _normalise_key(seq: str) -> str:
    parts = [p.strip().lower() for p in seq.split("+")]
    parts = [_KEY_ALIASES.get(p, p) for p in parts]
    return "+".join(parts)


def _binding_key(b: Binding) -> tuple:
    """Canonical hashable key for conflict detection."""
    if isinstance(b, KeyBinding):
        return ("key", _normalise_key(b.key))
    if isinstance(b, MouseBinding):
        return ("mouse", b.button, frozenset(b.modifiers), b.gesture)
    if isinstance(b, WheelBinding):
        return ("wheel", frozenset(b.modifiers), b.direction)
    return ("unknown", repr(b))


def _binding_to_dict(b: Binding) -> dict:
    if isinstance(b, KeyBinding):
        return {"kind": "key", "key": b.key}
    if isinstance(b, MouseBinding):
        return {
            "kind": "mouse",
            "button": b.button.value,
            "modifiers": sorted(m.value for m in b.modifiers),
            "gesture": b.gesture.value,
        }
    if isinstance(b, WheelBinding):
        return {
            "kind": "wheel",
            "modifiers": sorted(m.value for m in b.modifiers),
            "direction": b.direction,
        }
    raise TypeError(f"unknown binding type: {type(b).__name__}")


def _binding_from_dict(d: dict) -> Binding:
    kind = d.get("kind")
    if kind == "key":
        return KeyBinding(key=d["key"])
    if kind == "mouse":
        return MouseBinding(
            button=MouseButton(d["button"]),
            modifiers=frozenset(Modifier(m) for m in d.get("modifiers", [])),
            gesture=GestureKind(d.get("gesture", "press")),
        )
    if kind == "wheel":
        return WheelBinding(
            modifiers=frozenset(Modifier(m) for m in d.get("modifiers", [])),
            direction=d.get("direction", "any"),
        )
    raise ValueError(f"unknown binding kind: {kind!r}")


# Process-wide default registry. Widgets register against this on import
# unless they want their own private bindings (e.g. for an isolated test).
_DEFAULT: InputBindings | None = None


def get_default_bindings() -> InputBindings:
    """The process-wide default `InputBindings` registry."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = InputBindings()
    return _DEFAULT


__all__ = ["InputBindings", "get_default_bindings"]
