"""
Smart-match subtree density using resample for downsampling.

Uses the selected object as the reference and adjusts subtree objects to
match its polygon density. Same behavior as the Resample panel Match Density
row (SMART_RESAMPLE — not pure resample, not decimate-smart).

Room: Sculpt
Action: Resample-smart density matching on subtree of selected object
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Match subtree density via smart-resample against selected reference."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, mode=DensityMode.SMART_RESAMPLE)


main()
