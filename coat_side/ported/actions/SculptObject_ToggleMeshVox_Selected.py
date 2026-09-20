"""
Toggle Mesh/Voxel Same Polycount

This script toggles the current sculpt object between surface (mesh) and voxel modes
while attempting to maintain approximately the same polycount.

Room: Sculpt
Action: Toggle between surface and voxel modes, preserving polycount
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle between mesh and voxel modes while preserving polycount."""
    from ported.ops.SculptObject_ToggleMeshVox import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT)


main()
