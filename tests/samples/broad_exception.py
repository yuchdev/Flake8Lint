def risky() -> None:
    """Raise a placeholder failure."""
    raise RuntimeError


def handler() -> int:
    """Handle a broad exception."""
    try:
        risky()
    except Exception:
        return 1
