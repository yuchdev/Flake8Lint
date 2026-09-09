def parse(raw: str) -> int:
    """Return the parsed integer; the noqa is ignored outside allowed/."""
    try:
        return int(raw)
    except Exception:  # noqa
        return 0
