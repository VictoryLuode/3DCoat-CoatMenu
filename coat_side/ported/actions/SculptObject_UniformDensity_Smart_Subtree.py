"""
Smart uniform density adjustment for subtree using subdivide/decimate.

Unlike resample-based density matching, this method uses:
- Subdivision for increases > 2x (better shape preservation)
- Decimation for decreases
- Skip for objects close to target

This prevents meshes from being merged and preserves shape better.

Room: Sculpt
Action: Subdivide or decimate children to match parent's polygon density
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Smart density matching for all subtree objects."""
    from ported.ops.SculptObject_UniformDensity import main as op_main, DensityMode
    from ported.utils.scope_utils import Scope

    op_main(scope=Scope.TREE, mode=DensityMode.SMART)


main()

 # Collect subtree elements (excluding the reference itself)
 subtree: list[coat.SceneElement] = SceneAPI.collect_subtree(reference)
  children: list[coat.SceneElement] = [
       el for el in subtree
       if el != reference and el.isSculptObject()
       ]

   if not children:
        show_message("No child objects to process", 2000)
        return

    # Process each child
    subdivided: int = 0
    decimated: int = 0
    skipped: int = 0

    for child in children:
        result: str = smart_match_density(child, ref_vol)
        if result == "subdivided":
            subdivided += 1
        elif result == "decimated":
            decimated += 1
        else:
            skipped += 1

    # Restore selection
    reference.selectOne()

    show_message(
        f"Done: {subdivided} subdivided, {decimated} decimated, {skipped} skipped",
        3000
    )


main()
