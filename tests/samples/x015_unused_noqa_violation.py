"""Sample file demonstrating X015 unused `# noqa` violation."""


def compute() -> int:
    """Return a constant carrying a stray, unused `# noqa`."""
    value = 1  # noqa
    return value
