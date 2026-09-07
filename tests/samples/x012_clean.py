from typing import Union


def pick(flag: bool) -> Union[int, str]:
    """Return one of two concrete value types."""
    if flag:
        return 1
    return "value"
