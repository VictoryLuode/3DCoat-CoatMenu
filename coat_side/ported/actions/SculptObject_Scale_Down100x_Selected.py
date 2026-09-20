"""
Scale selected object down by 100x.

Room: Sculpt
Action: Apply 0.01 scale factor to selected object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Scale current object down by 100x (scale factor 0.01)."""
    from ported.ops.SculptObject_Scale import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, scale_factor=0.01)




main()
