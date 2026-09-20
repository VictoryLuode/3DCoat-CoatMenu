"""
Remesh a surface object while preserving its parts.

Decomposes the object into parts, remeshes each part (voxelize + back to surface),
then merges back together. This preserves the topology of separate parts.

Room: Sculpt
Action: Decompose, remesh each part, merge back
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Remesh object preserving parts via decompose and merge."""
    from ported.ops.SculptObject_RemeshPreserveParts import main as op_main
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.CURRENT)


main()
