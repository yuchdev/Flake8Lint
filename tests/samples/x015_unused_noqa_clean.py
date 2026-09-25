"""Sample file demonstrating a used `# noqa` (no X015)."""


def load() -> str:
    """Return a value while catching a broad exception that is suppressed."""
    try:
        value = "config"
    except Exception:  # noqa: X002
        value = "default"
    return value
