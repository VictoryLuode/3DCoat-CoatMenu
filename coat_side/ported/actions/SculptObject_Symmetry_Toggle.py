"""
Toggle global symmetry on/off.

Room: Sculpt
Action: Toggle symmetry enabled state via coat.symm API
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle symmetry on/off."""
    from ported.utils.symmetry_utils import toggle_symmetry

    toggle_symmetry()


main()
