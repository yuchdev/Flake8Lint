"""Numeric modulo and non-formatting `%` strings do not trigger X009."""


def remainder(count: int) -> int:
    """Return the remainder of dividing *count* by three."""
    return count % 3  # BinOp % but left operand is not a string literal


def progress_label() -> str:
    """Return a literal progress string containing a bare percent sign."""
    return "100% complete"  # plain string literal, never the left side of a `%` op
