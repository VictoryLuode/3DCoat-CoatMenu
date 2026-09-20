"""
Resample subtree objects to match the polygon density of the selected object.

Useful for evening out triangle sizes after using split tools, or preparing
for export with uniform mesh density.

Room: Sculpt
Action: Resamples all children to match parent's polygon density
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Resample all subtree objects to match reference density."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, mode=DensityMode.RESAMPLE)


main()

main()
