"""Explicit exception types are never bare, so X001 stays silent."""


def parse_int(raw: str) -> int:
    """Return the parsed integer, re-raising typed failures."""
    try:
        return int(raw)
    except (ValueError, TypeError) as exc:  # explicit tuple -> node.type is not None
        raise RuntimeError("cannot parse") from exc


def guard() -> str:
    """Return a marker after re-raising a broad but explicit base error."""
    try:
        result = "ok"
    except BaseException as exc:  # explicit type -> not bare (and not literal Exception)
        raise RuntimeError("failed") from exc
    return result
