"""
Isolate selected object (ghost all others).

Room: Sculpt
Action: Ghost all except selected (toggle isolation mode)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Isolate selection - ghost all except current selection."""
    from ported.ops.SculptObject_SetGhost import main as op_main, GhostMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, mode=GhostMode.ISOLATE)




main()
