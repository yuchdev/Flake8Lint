"""Catching a custom Exception subclass does not match literal `Exception` (no X002)."""


class ConfigError(Exception):
    """Raised when configuration is invalid."""


def load() -> str:
    """Return a config value, catching a domain-specific error."""
    try:
        value = "config"
    except ConfigError as exc:  # subclasses Exception but name is not literal `Exception`
        raise RuntimeError("bad config") from exc
    return value
