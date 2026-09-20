"""
Smart-match all sculpt objects' density using resample for downsampling.

Uses the selected object as the reference and adjusts all other sculpt objects
to match its polygon density. Same behavior as the Resample panel Match Density
row (SMART_RESAMPLE — not pure resample, not decimate-smart).

Room: Sculpt
Action: Resample-smart density matching on all sculpt objects
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Match all objects' density via smart-resample against selected reference."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.ALL, mode=DensityMode.SMART_RESAMPLE)


main()
