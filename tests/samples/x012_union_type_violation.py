"""Sample file demonstrating X012 Type1 | Type2 union annotation violation."""


def func_with_union(value: int | float) -> str:  # X012 – int | float param
    """Return the string form of an int-or-float value."""
    return str(value)
