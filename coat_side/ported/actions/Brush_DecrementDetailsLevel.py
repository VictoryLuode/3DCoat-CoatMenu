"""
Decrement Details Level

Decrements the brush details level by 0.5 and applies to all brush types
(and the live current-brush UI).

Room: Sculpt
Action: Decrement details level, apply to all brushes
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Decrement brush details level."""
    from ported.ops.Brush_DetailsLevel import adjust_details_level, DetailsLevelMode, ApplyScope

    adjust_details_level(
        mode=DetailsLevelMode.DECREMENT,
        apply_scope=ApplyScope.ALL,
    )


main()
