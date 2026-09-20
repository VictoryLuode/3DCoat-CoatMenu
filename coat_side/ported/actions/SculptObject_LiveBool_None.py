"""
Turn off live booleans on selected object.

Clears the live boolean mode on the currently selected sculpt object
(sets it to NONE), effectively disabling its boolean participation.

Room: Sculpt
Action: Disable live bool mode on selected element
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Turn off live booleans for the current element."""
    from ported.ops.SculptObject_LiveBool import main as op_main
    from ported.utils.SceneElement_boolean_utils import BooleanMode
    from ported.utils.scope_utils import Scope

    op_main(mode=BooleanMode.NONE, scope=Scope.CURRENT)


main()
