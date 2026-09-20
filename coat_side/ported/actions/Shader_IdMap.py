import coat
import math
# TODO: assign new id map to each object

active_element: coat.SceneElement = coat.Scene.current()

# if the scene root is ghosted, then we are already isolated
isolate_is_active = coat.Scene.sculptRoot().ghost()

# Iterate all elements. Enable their ghost if isolate is not active,
# disable if it is active
sculpt_root: coat.SceneElement = coat.Scene.sculptRoot()


def update_ghost(el: coat.SceneElement):
    el.setGhost(not isolate_is_active)


update_ghost(sculpt_root)

sculpt_root.iterateSubtree(update_ghost)


# Ensure the active element is not ghosted
coat.SceneElement.selectOne(active_element)
active_element.setGhost(False)

coat.ui.cmd("$select_PbrShaders/#0_LKS Matcap/LKS Metal Matcap 01/mcubes")

# Show summary message to user
coat.ui.showInfoMessage("Shader ID map applied", 3000)
