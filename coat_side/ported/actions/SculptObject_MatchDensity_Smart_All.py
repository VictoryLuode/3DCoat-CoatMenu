"""
Match polygon density across all sculpt objects using smart subdivision/decimation.

Uses the selected object as the reference and adjusts all other objects in the
entire sculpt tree to match its polygon density. Uses subdivide/decimate instead
of resampling for better shape preservation.

Room: Sculpt
Action: Smart density matching on all sculpt objects
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Match all objects to selected object's density using smart mode."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.ALL, mode=DensityMode.SMART)


main()
