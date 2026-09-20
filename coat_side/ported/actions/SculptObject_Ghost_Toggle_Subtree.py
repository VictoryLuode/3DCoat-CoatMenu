"""
Toggle ghost state for selected object and all children.

Room: Sculpt
Action: Toggle ghost on subtree (invert current state)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle ghost state for current element and its subtree."""
    from ported.ops.SculptObject_SetGhost import main as op_main, GhostMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, mode=GhostMode.INVERT)




main()
