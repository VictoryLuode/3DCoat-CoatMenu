"""
Run Autopo

Runs autopo on current sculpt object using cached settings.

Room: Sculpt
Action: Execute autopo with density/options from settings cache
"""
from ported.utils.action_base import action


@action
def main() -> None:
    """Execute the action."""
    from ported.utils.autopo_utils import run_autopo_with_settings

    # Execute autopo with cached settings
    run_autopo_with_settings()


main()
