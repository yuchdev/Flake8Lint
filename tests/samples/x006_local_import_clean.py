"""A module-level conditional import stays at depth 0 (no X006)."""

import sys

if sys.platform == "win32":
    import ntpath as _pathmod  # module-level `if` -> still depth 0, not a local import
else:
    import posixpath as _pathmod


def active_path_module() -> str:
    """Return the name of the platform-specific path module."""
    return _pathmod.__name__
