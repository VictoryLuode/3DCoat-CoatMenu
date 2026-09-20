"""
Fill each part in the subtree with a random ID color.

Useful for generating ID maps for texture baking. Each object in the
subtree gets a unique random color.

Room: Sculpt
Action: Fill each subtree object with unique random color
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Fill subtree with ID colors using operator."""
    from ported.ops.SculptObject_IdColors import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE)




main()
