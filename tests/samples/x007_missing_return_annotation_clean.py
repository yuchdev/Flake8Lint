"""A nested return value does not force an annotation on the outer scope (no X007)."""


def outer():
    """Build a helper class without returning a value from the outer scope."""

    class Inner:
        """Small helper exposing a computed value."""

        def value(self) -> int:
            """Return a constant integer."""
            return 7

    Inner().value()
