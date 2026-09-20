"""
Toggle symmetry plane visibility.

Room: Sculpt
Action: Toggle the symmetry plane visualization, persisted to LKS settings
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle symmetry plane visibility on/off."""
    from ported.utils.symmetry_utils import toggle_show_symmetry_plane

    toggle_show_symmetry_plane()


main()
