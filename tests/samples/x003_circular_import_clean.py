"""A module whose imports cannot form a cycle, so X003 stays silent.

Standard-library targets never enter the import graph, and the import guarded by
``if TYPE_CHECKING:`` does not run at import time, so neither can close a cycle
back to this module. This module is also fully clean under every other built-in
rule, so it doubles as a general clean fixture.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from collections.abc import Mapping


def render_payload(payload: Optional[Mapping[str, str]]) -> str:
    """Return the JSON rendering of the given payload."""
    if payload is None:
        return "{}"
    return json.dumps(dict(payload), sort_keys=True)
