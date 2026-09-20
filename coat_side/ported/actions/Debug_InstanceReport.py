"""
Debug: Instance Detection Report

Iterates the sculpt tree and reports which elements appear to share
the same underlying geometry (instances).

Tests multiple detection methods:
1. Volume == Volume comparison
2. getLinkedFile() - instances might share linked file
3. Polycount matching (heuristic)

Room: Sculpt
Action: Print instance detection report to console
"""
import coat
from ported.utils.scene_api import SceneAPI
from ported.utils.coat_ui_utils import show_message


def generate_instance_report() -> None:
    """Generate a report of potential instances in the sculpt tree."""
    root: coat.SceneElement | None = SceneAPI.get_sculpt_root()

    if not root:
        print("ERROR: No sculpt root found")
        show_message("No sculpt root found", 2000)
        return

    # Collect all sculpt objects
    all_elements: list[coat.SceneElement] = SceneAPI.collect_all_sculpt_objects()

    print("\n" + "=" * 60)
    print("INSTANCE DETECTION REPORT")
    print("=" * 60)
    print(f"Total sculpt objects found: {len(all_elements)}\n")

    # Collect detailed info for each element
    element_info: list[dict] = []

    for el in all_elements:
        name: str = el.name() or "(unnamed)"
        info: dict = {
            "name": name,
            "element": el,
            "is_sculpt": el.isSculptObject(),
            "linked_file": "",
            "polycount": 0,
            "volume": None,
            "valid": False,
        }

        # Try to get linked file
        try:
            info["linked_file"] = el.getLinkedFile() or ""
        except:
            pass

        if info["is_sculpt"]:
            vol = el.Volume()
            info["volume"] = vol
            if vol and vol.valid():
                info["valid"] = True
                info["polycount"] = vol.getPolycount()

        element_info.append(info)

    valid_items = [i for i in element_info if i["valid"]]
    print(f"Valid sculpt volumes: {len(valid_items)}")

    # Print all elements with details
    print("\n" + "-" * 40)
    print("ALL ELEMENTS:")
    print("-" * 40)
    for i, info in enumerate(element_info):
        linked = f" [linked: {info['linked_file']}]" if info['linked_file'] else ""
        polys = f" ({info['polycount']:,} polys)" if info['valid'] else " (invalid)"
        print(f"  [{i:2d}] {info['name']}{polys}{linked}")

    # Group by linked file (if any have links)
    print("\n" + "-" * 40)
    print("LINKED FILE GROUPING:")
    print("-" * 40)

    linked_groups: dict[str, list[dict]] = {}
    for info in element_info:
        if info["linked_file"]:
            key = info["linked_file"]
            if key not in linked_groups:
                linked_groups[key] = []
            linked_groups[key].append(info)

    if linked_groups:
        for file_path, items in linked_groups.items():
            print(f"\n  Linked to: {file_path}")
            for info in items:
                print(f"    - {info['name']}")
    else:
        print("  No elements have linked files.")

    # Group by polycount (heuristic - same polycount might be instances)
    print("\n" + "-" * 40)
    print("POLYCOUNT GROUPING (potential instances):")
    print("-" * 40)

    polycount_groups: dict[int, list[dict]] = {}
    for info in valid_items:
        pc = info["polycount"]
        if pc not in polycount_groups:
            polycount_groups[pc] = []
        polycount_groups[pc].append(info)

    # Only show groups with multiple elements
    multi_groups = {k: v for k, v in polycount_groups.items() if len(v) > 1}

    if multi_groups:
        print(
            f"\n  {len(multi_groups)} polycount values shared by multiple objects:")
        for polycount, items in sorted(multi_groups.items(), key=lambda x: -len(x[1])):
            print(f"\n  Polycount {polycount:,} ({len(items)} objects):")
            for info in items:
                print(f"    - {info['name']}")
    else:
        print("  No objects share the same polycount.")

    # Test Volume == comparison
    print("\n" + "-" * 40)
    print("VOLUME == COMPARISON:")
    print("-" * 40)

    groups: list[list[dict]] = []
    for info in valid_items:
        vol = info["volume"]
        found_group: bool = False

        for group in groups:
            ref_vol = group[0]["volume"]
            try:
                if vol == ref_vol:
                    group.append(info)
                    found_group = True
                    break
            except Exception as e:
                print(f"  Error comparing: {e}")

        if not found_group:
            groups.append([info])

    instance_groups = [g for g in groups if len(g) > 1]

    if instance_groups:
        print(f"\n  {len(instance_groups)} instance groups detected:")
        for i, group in enumerate(instance_groups):
            print(f"\n  Group {i + 1}:")
            for info in group:
                print(f"    - {info['name']} ({info['polycount']:,} polys)")
    else:
        print("  No instance groups detected via Volume ==.")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total elements: {len(all_elements)}")
    print(f"Valid volumes: {len(valid_items)}")
    print(f"Linked file groups: {len(linked_groups)}")
    print(f"Shared polycount groups: {len(multi_groups)}")
    print(f"Volume == groups: {len(instance_groups)}")
    print("=" * 60 + "\n")

    show_message("Instance report complete - check console", 3000)


generate_instance_report()

show_message(
    f"Report complete - {len(instance_groups)} instance groups", 3000)


generate_instance_report()
