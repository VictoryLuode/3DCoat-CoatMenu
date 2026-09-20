"""
Set live boolean mode to SUBTRACT on selected object.

Sets the live boolean SUBTRACT flag on the currently selected sculpt object.
Does NOT create a new child — use NewVoxBool for that.

Room: Sculpt
Action: Assign live bool SUBTRACT mode to selected element
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Set live boolean mode to SUBTRACT on the current element."""
    from ported.ops.SculptObject_LiveBool import main as op_main
    from ported.utils.SceneElement_boolean_utils import BooleanMode
    from ported.utils.scope_utils import Scope

    op_main(mode=BooleanMode.SUBTRACT, scope=Scope.CURRENT)


main()
