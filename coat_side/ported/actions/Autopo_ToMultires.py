"""
Autopo To Multiresolution

Runs autopo and imports result as multiresolution lowest level.

Room: Sculpt
Action: Autopo -> import as multiresolution
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Execute the action."""
    from ported.utils.autopo_utils import autopo_to_multiresolution

    # Execute autopo and import as multiresolution
    autopo_to_multiresolution()


main()
