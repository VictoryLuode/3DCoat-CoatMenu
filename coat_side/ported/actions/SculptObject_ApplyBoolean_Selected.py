"""
Apply (collapse) live-boolean subtree on selected sculpt object(s).

Calls Volume.collapseBollTree() on each selection. The selected element's
boolean suffix (`_Subtract|_Intersect|_Union`) is stripped post-collapse
since it is no longer a boolean child.

Room: Sculpt
Action: Collapse boolean subtree on selected
Requires: Sculpt object selected with a boolean subtree
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Apply boolean subtree on the current selection."""
    from ported.ops.SculptObject_ApplyBoolean import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, keep_original=False)


main()
