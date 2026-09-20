"""
Smart density matching for subtree using subdivide/decimate.

Uses the selected object as the reference and adjusts all subtree objects
to match its polygon density. Uses subdivide/decimate instead of resampling
for better shape preservation.

Room: Sculpt
Action: Smart density matching on subtree of selected object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Match subtree objects to selected object's density using smart mode."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, mode=DensityMode.SMART)


main()
