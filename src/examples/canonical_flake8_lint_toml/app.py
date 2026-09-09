def load(raw: str) -> int:
    """Return the parsed integer or a fallback when parsing fails."""
    try:
        return int(raw)
    except Exception:
        return 0
