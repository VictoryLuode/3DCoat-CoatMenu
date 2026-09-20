"""
Apply boolean on a duplicate; keep (and hide) the original.

Duplicates each selected sculpt object (with its boolean subtree),
collapses the boolean tree on the duplicate, hides the original.
The duplicate is renamed `<base>_Applied`.

Room: Sculpt
Action: Duplicate + apply booleans, hide original
Requires: Sculpt object selected with a boolean subtree
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Apply booleans on a duplicate while keeping the original hidden."""
    from ported.ops.SculptObject_ApplyBoolean import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT, keep_original=True)


main()
