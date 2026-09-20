"""
Add built-in Text mesh primitive to the sculpt scene.

Opens the parametric primitive tool and selects Text.

Room: Sculpt
Action: Open primitive tool and activate Text primitive
"""
from ported.utils.action_base import action


@action
def main() -> None:
    from ported.ops.Scene_AddPrimitive import add_builtin_primitive
    from ported.utils.primitives_constants import CMD_PRIM_TEXT
    add_builtin_primitive(CMD_PRIM_TEXT, "Text")


main()
