"""
Decimate selected object and all children to half polycount.

Room: Sculpt
Action: Decimate 50% on subtree
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Decimate subtree to half polycount."""
    from ported.ops.SculptObject_Decimate import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, reduction_percent=50.0)




main()
