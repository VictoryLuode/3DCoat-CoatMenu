"""
Set live boolean mode to INTERSECT on selected object.

Sets the live boolean INTERSECT flag on the currently selected sculpt object.
Does NOT create a new child — use NewVoxBool for that.

Room: Sculpt
Action: Assign live bool INTERSECT mode to selected element
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Set live boolean mode to INTERSECT on the current element."""
    from ported.ops.SculptObject_LiveBool import main as op_main
    from ported.utils.SceneElement_boolean_utils import BooleanMode
    from ported.utils.scope_utils import Scope

    op_main(mode=BooleanMode.INTERSECT, scope=Scope.CURRENT)


main()
