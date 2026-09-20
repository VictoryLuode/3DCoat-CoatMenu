"""
Add built-in Cylinder primitive to the sculpt scene.

Opens the parametric primitive tool and selects Cylinder.

Room: Sculpt
Action: Open primitive tool and activate Cylinder primitive
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_builtin_primitive
    from ported.utils.primitives_constants import CMD_PRIM_CYLINDER
    add_builtin_primitive(CMD_PRIM_CYLINDER, "Cylinder")


main()
