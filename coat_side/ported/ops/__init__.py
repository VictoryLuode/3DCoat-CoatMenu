"""
LKS Operators Package

Operators are configurable scripts that encapsulate reusable workflows.
Each operator has a main() function with explicit parameters for configuration and scope.

Action scripts (root level) and panel buttons both call operators,
ensuring consistent behavior across all entry points.

Naming Convention: <ObjectType>_<Action>.py
  - ObjectType: What the operator acts on (SculptObject, Brush, Scene, etc.)
  - Action: What it does (SetGhost, Decimate, IdColors, etc.)

Example:
  _ops/SculptObject_SetGhost.py
    main(ghost: bool, scope: Scope, invert: bool = False) -> int

Usage from action script:
  from ported.ops.SculptObject_SetGhost import main
  from ported.utils.scope_utils import Scope
  main(ghost=True, scope=Scope.ALL, invert=True)

Usage from panel button:
  def InvertGhost(self) -> None:
      from ported.ops.SculptObject_SetGhost import main
      from ported.utils.scope_utils import Scope
      main(ghost=True, scope=Scope.ALL, invert=True)
"""
