"""Build a QPalette from a Theme."""
from __future__ import annotations

from ported.lks_utils.theme.theme import Theme
from ported.lks_utils.gui_qt.theme.color_adapter import to_qcolor

import sys
# Initialize COM before Qt imports on Windows (clipboard requires apartment-threaded mode)
if sys.platform == "win32":
    try:
        import ctypes
        # Try apartment-threaded mode first for clipboard compatibility
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    except Exception:
        pass

from PySide6.QtGui import QPalette


def qpalette_for_theme(theme: Theme) -> QPalette:
    """Return a :class:`QPalette` populated from *theme*'s palette."""
    pal = QPalette()
    p = theme.palette

    # Window / general background
    pal.setColor(QPalette.ColorRole.Window, to_qcolor(p.panel_bg))
    pal.setColor(QPalette.ColorRole.WindowText, to_qcolor(p.text_primary))

    # Base (input fields, list views)
    pal.setColor(QPalette.ColorRole.Base, to_qcolor(p.input_bg))
    pal.setColor(QPalette.ColorRole.AlternateBase, to_qcolor(p.panel_bg_alt))
    pal.setColor(QPalette.ColorRole.Text, to_qcolor(p.input_fg))

    # Buttons
    pal.setColor(QPalette.ColorRole.Button, to_qcolor(p.button_bg))
    pal.setColor(QPalette.ColorRole.ButtonText, to_qcolor(p.button_fg))

    # Highlight (selection)
    pal.setColor(QPalette.ColorRole.Highlight, to_qcolor(p.selection))
    pal.setColor(QPalette.ColorRole.HighlightedText, to_qcolor(p.text_inverse))

    # Tooltip
    pal.setColor(QPalette.ColorRole.ToolTipBase, to_qcolor(p.overlay_bg))
    pal.setColor(QPalette.ColorRole.ToolTipText, to_qcolor(p.text_primary))

    # Link
    pal.setColor(QPalette.ColorRole.Link, to_qcolor(p.accent))

    # Disabled group mirrors the standard "muted" colour
    for role, muted_color in [
        (QPalette.ColorRole.WindowText, p.text_disabled),
        (QPalette.ColorRole.ButtonText, p.text_disabled),
        (QPalette.ColorRole.Text, p.text_disabled),
    ]:
        pal.setColor(QPalette.ColorGroup.Disabled,
                     role, to_qcolor(muted_color))

    return pal


__all__ = ["qpalette_for_theme"]
