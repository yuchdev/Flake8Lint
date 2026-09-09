"""`Optional[int]` and unions nested inside generics do not trigger X011."""
from typing import Optional


def lookup(key: str, default: Optional[int] = None) -> Optional[int]:
    """Return the stored value for *key* or the provided default."""
    values: list[int | None] = []  # nested union, not a top-level annotation
    if values:
        return values[0]
    return default
