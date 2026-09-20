"""
Add Cone mesh primitive to the sculpt scene.

Loads the SculptModel .obj file via the Merge tool.

Room: Sculpt
Action: Open Merge tool and select Cone.obj
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_mesh_primitive
    from ported.utils.primitives_constants import CMD_MESH_CONE
    add_mesh_primitive(CMD_MESH_CONE, "Cone")


main()
