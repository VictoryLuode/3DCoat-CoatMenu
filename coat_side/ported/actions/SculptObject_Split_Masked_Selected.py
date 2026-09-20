"""
Split the frozen/masked area of the current object into a new object.

Uses the SplitMasked operator which hides the frozen area, 
separates hidden geometry, and closes holes on resulting meshes.

Room: Sculpt
Action: Split frozen geometry into new object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Split frozen/masked area into a new object."""
    from ported.ops.SculptObject_SplitMasked import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT)


main()
