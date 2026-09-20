"""Action scripts that shipped with an older extension, ported into CoatMenu.

This folder is the ported addon root: ``ported.utils`` is what those scripts
imported as ``utils``, with ``ported.ops`` and ``ported.actions`` alongside.
Namespaced because every cExtension shares one interpreter - a bare ``utils``
or ``ops`` would collide with another add-on's.
"""
