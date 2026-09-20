"""
Create NEW intersect boolean child under selected object.

Clones the selected object, parents the clone under it, applies voxel extrusion
and assigns intersect boolean mode.  Extrusion is applied BEFORE boolean mode
to prevent a 3DCoat crash.

Room: Sculpt
Action: Clone selected → extrude → parent under it → set intersect boolean
Requires: Sculpt object selected; parent auto-voxelised if needed
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Create a new intersect boolean child under the current element."""
    from ported.ops.SculptObject_NewVoxBool import main as op_main
    from ported.utils.SceneElement_boolean_utils import BooleanMode

    op_main(mode=BooleanMode.INTERSECT)


main()
