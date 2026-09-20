"""
Autopo To Sculpt

Runs autopo, imports result to sculpt room as a sibling of original,
and ghosts the original object.

Room: Sculpt
Action: Autopo -> import to sculpt -> reparent -> ghost original
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Execute the action."""
    from ported.utils.autopo_utils import autopo_to_sculpt

    # Execute
    autopo_to_sculpt()


main()
