"""
Show all objects in scene.

Room: Sculpt
Action: Show all objects in the sculpt tree (make all visible)
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Show all objects in sculpt tree."""
    from ported.ops.SculptObject_Visibility import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.ALL, visible=True)


main()
