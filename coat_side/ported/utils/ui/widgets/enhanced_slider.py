"""EnhancedSlider — re-exported from ported.lks_utils for backward compatibility."""
from __future__ import annotations

from ported.lks_utils.gui_qt.widgets.enhanced_slider import QEnhancedSlider

# Backward-compatibility alias for code still importing EnhancedSlider
EnhancedSlider = QEnhancedSlider

__all__ = ["QEnhancedSlider", "EnhancedSlider"]
