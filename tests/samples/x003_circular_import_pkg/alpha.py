"""Sample module demonstrating the X003 circular import violation."""

from .beta import BETA_LABEL  # X003 - beta imports alpha straight back

ALPHA_LABEL = f"alpha of {BETA_LABEL}"
