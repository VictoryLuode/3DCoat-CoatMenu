"""
Toggle mirror symmetry for the X axis.

Room: Sculpt
Action: Toggle X-axis mirror symmetry on/off (no geometry change)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle X-axis mirror symmetry."""
    from ported.ops.SculptObject_Mirror import main as op_main

    op_main(axis="X")


main()
