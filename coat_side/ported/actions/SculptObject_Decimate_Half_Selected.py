"""
Decimate selected object to 50% of its original polycount.

Room: Sculpt
Action: Decimate 50% on selected object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Decimate selected object to half its polycount."""
    from ported.ops.SculptObject_Decimate import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, reduction_percent=50.0)


main()
