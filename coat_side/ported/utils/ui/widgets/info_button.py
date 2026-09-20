"""InfoButton / InfoPopup / InfoButtonCompact — re-exported from ported.lks_utils.

The canonical implementations live in ``ported.lks_utils.gui_qt.widgets.info_button``:
- ``QInfoButton`` — standard square button with accent-blue circular ``?`` icon
- ``QInfoButtonCompact`` — compact circular ``?`` button for inline use
- ``QInfoPopup`` — floating help-text popup panel

Backward-compatible aliases (without the Q prefix) are provided here
so existing 3DCoat code continues to work unchanged.
"""
from __future__ import annotations

from ported.lks_utils.gui_qt.widgets.info_button import (
    QInfoPopup,
    QInfoButton,
    QInfoButtonCompact,
)

# Backward-compatible aliases
InfoPopup = QInfoPopup
InfoButton = QInfoButton
InfoButtonCompact = QInfoButtonCompact

__all__ = ["InfoButton", "InfoButtonCompact", "InfoPopup"]
