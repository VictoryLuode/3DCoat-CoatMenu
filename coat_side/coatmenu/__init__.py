"""CoatMenu - private package.

Namespaced on purpose: every cExtension shares one process, so a
top-level ``core`` or ``ui`` package would collide with another
add-on's (a sibling extension shipping its own ``ui`` wins when it imports
first).
"""

# Kept in step with the git tag; the release zip is named after it and the
# doctor report prints it.
__version__ = "0.6.1"
