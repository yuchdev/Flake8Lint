"""Explicit pytest helper APIs for flake8-lint."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .api import format_text, lint_paths
from .config import LintConfig


def assert_lint_clean(*paths: str | Path, config: LintConfig | None = None) -> None:
    selected: Iterable[str | Path] = paths or (Path.cwd(),)
    result = lint_paths(selected, config=config)
    if not result.ok:
        raise AssertionError(format_text(result))
