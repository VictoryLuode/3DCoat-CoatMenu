from ported.utils.action_base import action


@action
def main() -> None:
    el = coat.Scene.current()
    # Scale down by 100 means using a scale factor of 0.01.
    scale_selected_element(el, 100.0)
    coat.ui.cmd("$ExportPatternForMerge")
    scale_selected_element(el, 0.01)




main()
