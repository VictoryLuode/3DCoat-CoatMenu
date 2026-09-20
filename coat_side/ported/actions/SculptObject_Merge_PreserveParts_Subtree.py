"""
Merge subtree while preserving parts in surface mode.

Converts all objects in the subtree to surface mode (collapsing boolean trees),
then merges them together while preserving their separate part identities.

Room: Sculpt
Action: Convert all to surface, then merge subtree
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Merge subtree preserving parts in surface mode."""
    from ported.ops.SculptObject_MergePreserveParts import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE)


main()
