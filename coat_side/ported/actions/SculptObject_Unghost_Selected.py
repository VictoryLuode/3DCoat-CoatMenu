"""
Unghost selected object.

Room: Sculpt
Action: Remove ghost state from selected object (makes it fully opaque)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Unghost selected object."""
    from ported.ops.SculptObject_SetGhost import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, ghost=False)


main()
