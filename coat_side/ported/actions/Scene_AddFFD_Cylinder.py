"""
Add FFD Cylinder + FFD to the sculpt scene.

Opens the parametric primitive tool and selects Cylinder FFD shape.

Room: Sculpt
Action: Open primitive tool and activate Cylinder FFD primitive
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_ffd_primitive
    from ported.utils.primitives_constants import CMD_FFD_CYLINDER
    add_ffd_primitive(CMD_FFD_CYLINDER, "FFD Cylinder")


main()
