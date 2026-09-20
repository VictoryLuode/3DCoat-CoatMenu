"""
Scale selected object up by 100x.

Room: Sculpt
Action: Apply 100x scale factor to selected object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Scale current object up by 100x (scale factor 100.0)."""
    from ported.ops.SculptObject_Scale import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, scale_factor=100.0)




main()
