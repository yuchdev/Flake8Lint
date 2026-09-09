def bare(raw: str) -> int:
    """Return the parsed integer, swallowing errors with a bare except."""
    try:
        return int(raw)
    except:  # noqa: E722
        return 0
