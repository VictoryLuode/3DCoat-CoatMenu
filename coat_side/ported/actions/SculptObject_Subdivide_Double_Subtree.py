"""
Subdivide selected object and all children (double polycount).

Room: Sculpt
Action: Subdivide subtree (approximately 2x polycount)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Subdivide current object and subtree."""
    from ported.ops.SculptObject_Subdivide import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, subdivisions=1)




main()
