def pick(flag: bool) -> int | str:
    """Return one of two concrete value types."""
    if flag:
        return 1
    return "value"
