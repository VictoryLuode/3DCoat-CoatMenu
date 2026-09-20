"""
Toggle Isolate Visible - Selected

Toggles visibility isolation mode: if currently isolated, show all;
otherwise hide all except selected elements.

Room: Sculpt
Action: Toggle visibility isolation state on selection
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Execute the action."""
    from ported.utils.scene_api import SceneAPI, SelectionAPI
    from ported.utils.SceneElement_visibility_utils import toggle_visibility_isolation
    from ported.utils.coat_ui_utils import show_message

    # Get current selection
    selection = SelectionAPI.save_selection()
    if not selection:
        show_message("No object selected", 2000)
        return

    # Get all sculpt objects (uses iterateSubtree which includes hidden)
    all_elements = SceneAPI.collect_all_sculpt_objects()
    if not all_elements:
        show_message("No sculpt objects", 2000)
        return

    # Toggle visibility isolation
    is_isolated, count = toggle_visibility_isolation(all_elements, selection)

    if is_isolated:
        show_message(f"Visibility isolated {len(selection)} object(s)", 2000)
    else:
        show_message(f"Showed {count} objects", 2000)


main()
