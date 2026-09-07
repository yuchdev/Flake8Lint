"""Public package interface for flake8-lint."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .api import LintResult, Rule, RuleContext, RuleViolation, check_file, check_tree, lint_paths


def _detect_version() -> str:
    try:
        return version("flake8-lint")
    except PackageNotFoundError:
        return "1.0.0"


__version__ = _detect_version()

__all__ = [
    "LintResult",
    "Rule",
    "RuleContext",
    "RuleViolation",
    "__version__",
    "check_file",
    "check_tree",
    "lint_paths",
]
