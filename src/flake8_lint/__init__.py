"""Public package interface for flake8-lint."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .api import (
    LintResult,
    Rule,
    RuleContext,
    RuleViolation,
    check_file,
    check_source,
    check_tree,
    lint_paths,
)
from .registry import RuleRegistry


def _detect_version() -> str:
    """Return the installed distribution version, or a default fallback."""
    try:
        return version("flake8-lint")
    except PackageNotFoundError:
        # Metadata is unavailable when running from an uninstalled source tree.
        fallback_version = "1.0.0"
        return fallback_version


__version__ = _detect_version()

__all__ = [
    "LintResult",
    "Rule",
    "RuleContext",
    "RuleViolation",
    "__version__",
    "check_file",
    "check_source",
    "check_tree",
    "lint_paths",
    "RuleRegistry",
]
