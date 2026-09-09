"""Re-raising in the handler means the import failure is not suppressed (no X010)."""

try:
    import optional_dependency
except ImportError as exc:  # handler re-raises, so the failure is not swallowed
    raise RuntimeError("optional_dependency is required") from exc
