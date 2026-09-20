"""
Toggle mirror symmetry for the Z axis.

Room: Sculpt
Action: Toggle Z-axis mirror symmetry on/off (no geometry change)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle Z-axis mirror symmetry."""
    from ported.ops.SculptObject_Mirror import main as op_main

    op_main(axis="Z")


main()
