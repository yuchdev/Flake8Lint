"""Logging before `pass` means the handler body is not all-muting (no X004)."""


def func_with_logged_except() -> str:
    """Return a status while reporting caught errors instead of muting them."""
    try:
        value = int("1")
    except ValueError:  # body has a non-muting print, so not all statements mute
        print("caught a value error")
    return "done"
