"""
Ghost selected object.

Room: Sculpt
Action: Ghost the currently selected object (makes it semi-transparent)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Ghost selected object."""
    from ported.ops.SculptObject_SetGhost import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, ghost=True)


main()
