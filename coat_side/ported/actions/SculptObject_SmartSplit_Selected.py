"""
Smart split: separates hidden geometry (voxel) or masked/frozen area (surface).

Adapts based on object mode:
- Voxel mode: Splits hidden geometry directly
- Surface mode: Hides masked/frozen area first, then splits

Room: Sculpt
Action: Smart split hidden/masked area into new object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Smart split hidden or masked area into new object(s)."""
    from ported.ops.SculptObject_SmartSplit import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT)


main()
