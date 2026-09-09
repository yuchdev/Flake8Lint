"""X003 is permanently reserved and disabled, so it never emits a violation.

Even a ``Settings.set()`` method, the shape a custom ``SETTINGS_SET`` rule might
target, produces no X003 diagnostic: the reserved rule always returns zero
results regardless of module content. This module is also fully clean under all
other built-in rules so it can double as a general clean fixture.
"""


class Settings:
    """A minimal mutable settings holder."""

    def __init__(self):
        """Initialise an empty settings store."""
        self._data: dict = {}

    def set(self, key: str, value: str):
        """Store the given value under the given key."""
        self._data[key] = value
