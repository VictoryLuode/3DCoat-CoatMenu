"""
LKS Settings - Persistent settings cache for LKS tools.

Provides singleton settings objects with attribute access that
persist to JSON files across 3DCoat sessions.

Folder organization (in data/):
- state/: User-specific settings and UI state (local only, not pushed to remote)
  - lks_brush_settings.json: Brush settings (details_level, auto_subdivide, etc.)
  - lks_autopo_settings.json: Autopo workflow configuration
  - lks_settings.json: General/other settings
  - lks_ui_state.json: UI panel states (collapsible sections, etc.)
- defaults/: Default config templates (tracked in repo)
- schemas/: JSON validation schemas (tracked in repo)
- logs/: Debug logs (local only)
"""
import coat
import json
import os
from pathlib import Path

# =============================================================================
# FILE PATHS
# =============================================================================

# Data folder paths (relative to this module)
_DATA_DIR: Path = Path(__file__).parent.parent / "data"
_STATE_DIR: Path = _DATA_DIR / "state"

# File names (stored in data/state/ folder)
BRUSH_SETTINGS_FILE: str = "lks_brush_settings.json"
AUTOPO_SETTINGS_FILE: str = "lks_autopo_settings.json"
GENERAL_SETTINGS_FILE: str = "lks_settings.json"


def _get_brush_settings_path() -> str:
    """Get the absolute path to brush settings file (in data/state/)."""
    return str(_STATE_DIR / BRUSH_SETTINGS_FILE)


def _get_autopo_settings_path() -> str:
    """Get the absolute path to autopo settings file (in data/state/)."""
    return str(_STATE_DIR / AUTOPO_SETTINGS_FILE)


def _get_general_settings_path() -> str:
    """Get the absolute path to general settings file (in data/state/)."""
    return str(_STATE_DIR / GENERAL_SETTINGS_FILE)

# =============================================================================
# DEFAULTS
# =============================================================================


# Brush settings defaults
BRUSH_DEFAULTS: dict = {
    "details_level": 1,
    "auto_subdivide": True,
    "remove_stretching": True,
}

# Autopo settings defaults (separate file)
AUTOPO_DEFAULTS: dict = {
    "autopo_polycount": 10000,
    "autopo_capture_details": 1.0,  # 0.0-1.0 (1.0 = 100%)
    "autopo_auto_density": 0.5,  # 0.0-2.0 (painted density influence)
    "autopo_hardsurface": False,
    "autopo_voxelize": False,
    "autopo_voxelize_polycount": 1000,  # x1000 polys (1000 = 1M)
    "autopo_decimate_if_above": False,
    "autopo_decimation_limit": 10,  # x1000 polys (10 = 10k)
    "autopo_tangent_smooth": True,
    "autopo_bypass_density_modal": True,
    "autopo_quality": "intermediate",  # "draft", "intermediate", "best"
}

# General settings defaults (decimate, etc. - NOT autopo)
GENERAL_DEFAULTS: dict = {
    "decimate_reduction": 50,
    "dev_mode": False,  # When True, action scripts reload all modules before invoke
    "show_symmetry_plane": True,  # Persisted by symmetry_utils.toggle_show_symmetry_plane()
}

# Radial menu settings defaults
RADIAL_MENU_DEFAULTS: dict = {
    # Pixels - no selection within this radius
    "radial_menu_dead_zone_radius": 75,
    # Pixels - distance from anchor to item centers
    "radial_menu_menu_radius": 150,
    # Pixels - hover detection radius for branches/exit
    "radial_menu_branch_hover_radius": 20,
    # Milliseconds - dwell time before submenu entry/exit
    "radial_menu_branch_dwell_ms": 250,
    # Default trigger key (user assignable)
    "radial_menu_trigger_key": "Q",
}

# Combined defaults for backward compatibility
DEFAULTS: dict = {**BRUSH_DEFAULTS, **AUTOPO_DEFAULTS,
                  **GENERAL_DEFAULTS, **RADIAL_MENU_DEFAULTS}


# =============================================================================
# BRUSH SETTINGS (separate singleton for brush-specific settings)
# =============================================================================

class BrushSettings:
    """
    Singleton for brush-specific settings.

    Stored in lks_brush_settings.json for isolation from other settings.
    Uses native Python json for reliable read/write.

    Usage:
        settings = get_brush_settings()
        print(settings.details_level)
        settings.details_level = 5
        save_brush_settings()
    """
    _instance = None

    def __init__(self):
        self._data: dict = dict(BRUSH_DEFAULTS)
        self._load()

    def _load(self) -> None:
        """Load settings from JSON file if it exists."""
        file_path: str = _get_brush_settings_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded: dict = json.load(f)
                    self._data.update(loaded)
                    print(
                        f"[BrushSettings] Loaded from {file_path}: {self._data}")
            except Exception as e:
                print(f"[BrushSettings] Failed to load: {e}")
                # If load fails, keep defaults

    def _save(self) -> None:
        """Save settings to JSON file."""
        file_path: str = _get_brush_settings_path()
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
            print(f"[BrushSettings] Saved to {file_path}: {self._data}")
        except Exception as e:
            print(f"[BrushSettings] Failed to save: {e}")

    def __getattr__(self, name: str):
        """Get setting value by attribute access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name, BRUSH_DEFAULTS.get(name))

    def __setattr__(self, name: str, value):
        """Set setting value by attribute access."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def to_dict(self) -> dict:
        """Return settings as dictionary."""
        return dict(self._data)


def get_brush_settings() -> BrushSettings:
    """Get or create the brush settings singleton instance."""
    if BrushSettings._instance is None:
        BrushSettings._instance = BrushSettings()
    return BrushSettings._instance


def save_brush_settings() -> None:
    """Persist brush settings to disk using native Python JSON."""
    settings = get_brush_settings()
    settings._save()


def reload_brush_settings() -> None:
    """Force reload brush settings from disk (clears singleton)."""
    BrushSettings._instance = None


# =============================================================================
# AUTOPO SETTINGS (separate singleton for autopo-specific settings)
# =============================================================================

class AutopoSettings:
    """
    Singleton for autopo-specific settings.

    Stored in lks_autopo_settings.json for isolation from other settings.
    Uses native Python json for reliable read/write.

    Usage:
        settings = get_autopo_settings()
        print(settings.autopo_polycount)
        settings.autopo_polycount = 5000
        save_autopo_settings()
    """
    _instance = None

    def __init__(self):
        self._data: dict = dict(AUTOPO_DEFAULTS)
        self._load()

    def _load(self) -> None:
        """Load settings from JSON file if it exists."""
        file_path: str = _get_autopo_settings_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded: dict = json.load(f)
                    self._data.update(loaded)
                    print(
                        f"[AutopoSettings] Loaded from {file_path}: {self._data}")
            except Exception as e:
                print(f"[AutopoSettings] Failed to load: {e}")

    def _save(self) -> None:
        """Save settings to JSON file."""
        file_path: str = _get_autopo_settings_path()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
            print(f"[AutopoSettings] Saved to {file_path}: {self._data}")
        except Exception as e:
            print(f"[AutopoSettings] Failed to save: {e}")

    def __getattr__(self, name: str):
        """Get setting value by attribute access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name, AUTOPO_DEFAULTS.get(name))

    def __setattr__(self, name: str, value):
        """Set setting value by attribute access."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def to_dict(self) -> dict:
        """Return settings as dictionary."""
        return dict(self._data)


def get_autopo_settings() -> AutopoSettings:
    """Get or create the autopo settings singleton instance."""
    if AutopoSettings._instance is None:
        AutopoSettings._instance = AutopoSettings()
    return AutopoSettings._instance


def save_autopo_settings() -> None:
    """Persist autopo settings to disk using native Python JSON."""
    settings = get_autopo_settings()
    settings._save()


def reload_autopo_settings() -> None:
    """Force reload autopo settings from disk (clears singleton)."""
    AutopoSettings._instance = None


# =============================================================================
# GENERAL SETTINGS (decimate, etc. - NOT autopo)
# =============================================================================

class LKSSettings:
    """
    Singleton for general LKS settings (decimate, radial menu, etc.).

    Stored in lks_settings.json. Uses native Python json.
    NOTE: Autopo settings are now in AutopoSettings class.
    NOTE: Brush settings are in BrushSettings class.

    Usage:
        settings = get_settings()
        print(settings.decimate_reduction)  # Read
        settings.decimate_reduction = 60    # Write (in memory)
        save_settings()                     # Persist to disk
    """
    _instance = None

    def __init__(self):
        self._data: dict = dict(GENERAL_DEFAULTS)
        self._load()

    def _load(self) -> None:
        """Load settings from JSON file if it exists."""
        file_path: str = _get_general_settings_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded: dict = json.load(f)
                    self._data.update(loaded)
                    print(
                        f"[LKSSettings] Loaded from {file_path}: {self._data}")
            except Exception as e:
                print(f"[LKSSettings] Failed to load: {e}")

    def _save(self) -> None:
        """Save settings to JSON file."""
        file_path: str = _get_general_settings_path()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
            print(f"[LKSSettings] Saved to {file_path}: {self._data}")
        except Exception as e:
            print(f"[LKSSettings] Failed to save: {e}")

    def __getattr__(self, name: str):
        """Get setting value by attribute access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name, GENERAL_DEFAULTS.get(name))

    def __setattr__(self, name: str, value):
        """Set setting value by attribute access."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def get(self, name: str, default=None):
        """Get setting value with optional default."""
        return self._data.get(name, default if default is not None else GENERAL_DEFAULTS.get(name))

    def set(self, name: str, value):
        """Set setting value."""
        self._data[name] = value

    def to_dict(self) -> dict:
        """Return settings as dictionary."""
        return dict(self._data)


def get_settings() -> LKSSettings:
    """Get or create the singleton settings instance."""
    if LKSSettings._instance is None:
        LKSSettings._instance = LKSSettings()
    return LKSSettings._instance


def save_settings() -> None:
    """Persist general settings to disk using native Python JSON."""
    settings = get_settings()
    settings._save()


def reload_settings() -> None:
    """Force reload settings from disk (clears singleton)."""
    LKSSettings._instance = None


def reset_settings() -> None:
    """Reset settings to defaults and save."""
    settings = get_settings()
    settings._data = dict(GENERAL_DEFAULTS)
    save_settings()


# =============================================================================
# UI STATE SETTINGS (separate singleton for UI panel states)
# =============================================================================

UI_STATE_FILE: str = "lks_ui_state.json"


def _get_ui_state_path() -> str:
    """Get the absolute path to UI state file (in data/state/)."""
    return str(_STATE_DIR / UI_STATE_FILE)


# UI state defaults (collapsible section states, etc.)
UI_STATE_DEFAULTS: dict = {
    # Collapsible section expanded states (True = expanded)
    "section_decimate_expanded": True,
    "section_proxy_expanded": False,
    "section_resample_expanded": False,
    "section_mode_expanded": False,
    "section_scale_expanded": False,
    "section_visibility_ghost_expanded": True,
    "section_subdiv_expanded": False,
    "section_smart_expanded": False,
    "section_autopo_expanded": False,
    "section_layers_expanded": False,
    "section_booleans_expanded": False,
    # Panel window settings
    "panel_always_on_top": False,
    # First-launch & tab tracking
    "panel_has_been_launched": False,
    "active_tab_index": 0,
}


class UIStateSettings:
    """
    Singleton for UI state persistence.

    Stored in lks_ui_state.json to track panel section states across sessions.
    Uses native Python json for reliable read/write.

    Usage:
        ui_state = get_ui_state()
        print(ui_state.section_decimate_expanded)
        ui_state.section_decimate_expanded = False
        save_ui_state()
    """
    _instance = None

    def __init__(self):
        self._data: dict = dict(UI_STATE_DEFAULTS)
        self._load()

    def _load(self) -> None:
        """Load UI state from JSON file if it exists."""
        file_path: str = _get_ui_state_path()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded: dict = json.load(f)
                    self._data.update(loaded)
                    print(f"[UIState] Loaded from {file_path}: {self._data}")
            except Exception as e:
                print(f"[UIState] Failed to load: {e}")

    def _save(self) -> None:
        """Save UI state to JSON file."""
        file_path: str = _get_ui_state_path()
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2)
            print(f"[UIState] Saved to {file_path}: {self._data}")
        except Exception as e:
            print(f"[UIState] Failed to save: {e}")

    def __getattr__(self, name: str):
        """Get state value by attribute access."""
        if name.startswith('_'):
            return super().__getattribute__(name)
        return self._data.get(name, UI_STATE_DEFAULTS.get(name))

    def __setattr__(self, name: str, value):
        """Set state value by attribute access."""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def to_dict(self) -> dict:
        """Return UI state as dictionary."""
        return dict(self._data)


def get_ui_state() -> UIStateSettings:
    """Get or create the UI state singleton instance."""
    if UIStateSettings._instance is None:
        UIStateSettings._instance = UIStateSettings()
    return UIStateSettings._instance


def save_ui_state() -> None:
    """Persist UI state to disk using native Python JSON."""
    ui_state = get_ui_state()
    ui_state._save()


def reload_ui_state() -> None:
    """Force reload UI state from disk (clears singleton)."""
    UIStateSettings._instance = None


def reset_ui_state() -> None:
    """Reset UI state to defaults and save."""
    ui_state = get_ui_state()
    ui_state._data = dict(UI_STATE_DEFAULTS)
    save_ui_state()
