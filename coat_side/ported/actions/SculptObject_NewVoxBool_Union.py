"""
Create NEW union boolean child under selected object.

Clones the selected object, parents the clone under it, and assigns union boolean mode.

Room: Sculpt
Action: Clone selected → parent under it → set union boolean
Requires: Sculpt object selected; parent auto-voxelised if needed
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Create a new union boolean child under the current element."""
    from ported.ops.SculptObject_NewVoxBool import main as op_main
    from ported.utils.SceneElement_boolean_utils import BooleanMode

    op_main(mode=BooleanMode.UNION)


main()
