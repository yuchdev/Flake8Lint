"""The other half of the X003 cycle: beta imports alpha, alpha imports beta."""

from .alpha import ALPHA_LABEL  # X003 - closes the cycle back to alpha

BETA_LABEL = f"beta of {ALPHA_LABEL}"
