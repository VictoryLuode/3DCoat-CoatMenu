"""
Add Capsule mesh primitive to the sculpt scene.

Loads the SculptModel .obj file via the Merge tool.

Room: Sculpt
Action: Open Merge tool and select Capsule.obj
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_mesh_primitive
    from ported.utils.primitives_constants import CMD_MESH_CAPSULE
    add_mesh_primitive(CMD_MESH_CAPSULE, "Capsule")


main()
