"""A `-> None` stub body (single `...`) is exempt from X008.

The stub function has no docstring, so this fixture still trips X005; it is
asserted clean only for its target code, X008.
"""


def write(data: str) -> None: ...
