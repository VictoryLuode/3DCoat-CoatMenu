"""
Fast reimport system using a custom MetaPathFinder.

Problem:
    3DCoat imports action scripts as Python modules. When we clear a module
    from sys.modules (so it re-executes on next hotkey press), 3DCoat's
    internal reimport takes ~1 second due to its C++ dispatch overhead.

Solution:
    Install a custom MetaPathFinder at the FRONT of sys.meta_path. After an
    action script runs, we cache its compiled code object. When 3DCoat's
    import triggers Python's import machinery, our finder intercepts FIRST
    and serves the cached bytecode instantly (~1ms vs ~1000ms).

Usage:
    # In postprocess (LKS.py):
    from ported.utils.fast_reimport import FastReimportFinder
    finder = FastReimportFinder.get_instance()
    finder.cache_module(module_name)   # cache before clearing
    del sys.modules[module_name]       # clear so 3DCoat reimports

    # Next hotkey press: our finder serves cached code → instant execution.

    # In dev_mode: skip caching so code changes are picked up normally.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
import time
import types
from typing import Any, Sequence


class _CachedCodeLoader(importlib.abc.Loader):
    """Loader that executes a pre-compiled code object."""

    def __init__(self, code: types.CodeType, filepath: str) -> None:
        self._code: types.CodeType = code
        self._filepath: str = filepath

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> None:
        return None  # Use default module creation

    def exec_module(self, module: types.ModuleType) -> None:
        module.__file__ = self._filepath
        exec(self._code, module.__dict__)


class FastReimportFinder(importlib.abc.MetaPathFinder):
    """
    Custom MetaPathFinder that caches compiled code objects for instant reimport.

    When a module is cached and then deleted from sys.modules, the next import
    goes through sys.meta_path. Our finder (installed at position 0) intercepts
    and serves the pre-compiled code without any file I/O or 3DCoat overhead.
    """

    _instance: FastReimportFinder | None = None

    def __init__(self) -> None:
        # module_name -> (code_object, filepath)
        self._cache: dict[str, tuple[types.CodeType, str]] = {}

    @classmethod
    def get_instance(cls) -> FastReimportFinder:
        """Get or create the singleton finder and install it in sys.meta_path."""
        if cls._instance is None:
            cls._instance = cls()
            sys.meta_path.insert(0, cls._instance)
            print("[FastReimport] Installed MetaPathFinder at sys.meta_path[0]")
        return cls._instance

    def cache_module(self, name: str) -> bool:
        """
        Cache a module's compiled code object for fast reimport.

        Call this BEFORE deleting the module from sys.modules.
        Returns True if the module was successfully cached.
        """
        mod: types.ModuleType | None = sys.modules.get(name)
        if mod is None:
            return False

        filepath: str | None = getattr(mod, '__file__', None)
        if filepath is None:
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source: str = f.read()
            code: types.CodeType = compile(source, filepath, 'exec')
            self._cache[name] = (code, filepath)
            return True
        except Exception as e:
            print(f"[FastReimport] Failed to cache {name}: {e}")
            return False

    def uncache_module(self, name: str) -> None:
        """Remove a module from the fast reimport cache (e.g. for dev_mode)."""
        self._cache.pop(name, None)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        """Called by Python's import machinery when looking for a module."""
        if fullname not in self._cache:
            return None

        code: types.CodeType
        filepath: str
        code, filepath = self._cache[fullname]

        t0: float = time.monotonic()
        loader: _CachedCodeLoader = _CachedCodeLoader(code, filepath)
        spec: importlib.machinery.ModuleSpec = importlib.machinery.ModuleSpec(
            fullname, loader, origin=filepath,
        )
        elapsed_ms: float = (time.monotonic() - t0) * 1000
        print(f"[FastReimport] Serving cached code for {fullname} "
              f"(spec created in {elapsed_ms:.1f}ms)")
        return spec

    def is_cached(self, name: str) -> bool:
        """Check if a module is in the fast reimport cache."""
        return name in self._cache

    def clear_all(self) -> None:
        """Clear all cached code objects."""
        self._cache.clear()
