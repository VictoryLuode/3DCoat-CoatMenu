"""
Apply Dynamic Subdiv Settings

Applies cached brush settings (auto_subdivide, details_level, remove_stretching)
to all brush types.

Room: Sculpt
Action: Apply cached dynamic subdiv settings to all brushes
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Apply dynamic subdiv settings to all brushes."""
    from ported.ops.Brush_DetailsLevel import apply_all_brush_settings

    apply_all_brush_settings()


main()
