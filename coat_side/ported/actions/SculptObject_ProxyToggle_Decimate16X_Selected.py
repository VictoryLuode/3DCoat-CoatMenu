"""
Toggle Decimate 16X proxy mode for selected object.

Room: Sculpt
Action: Toggle 16X decimation proxy for faster viewport performance
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Toggle Decimate 16X proxy on selected object."""
    from ported.ops.SculptObject_Proxy import main as op_main
    from ported.utils.scope_utils import Scope
    from ported.utils.Volume_proxy_utils import ProxyMode

    op_main(scope=Scope.CURRENT, proxy_mode=ProxyMode.DECIMATE_16X)


main()
