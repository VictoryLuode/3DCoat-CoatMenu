"""
Invert ghost state for all objects in scene.

Room: Sculpt
Action: Invert ghost state (ghosted→unghosted, unghosted→ghosted)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Invert ghost state for all objects."""
    from ported.ops.SculptObject_SetGhost import main as op_main, GhostMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.ALL, mode=GhostMode.INVERT)




main()
