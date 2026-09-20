"""
Add FFD Flat disc + FFD to the sculpt scene.

Opens the parametric primitive tool and selects Disc FFD shape.

Room: Sculpt
Action: Open primitive tool and activate Disc FFD primitive
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_ffd_primitive
    from ported.utils.primitives_constants import CMD_FFD_DISC
    add_ffd_primitive(CMD_FFD_DISC, "FFD Disc")


main()
