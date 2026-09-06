"""Thin Flake8 adapter for built-in flake8-lint rules."""

from __future__ import annotations

from pathlib import Path

from . import __version__
from .api import check_tree
from .config import LintConfig
from .registry import resolve_registry


class ProjectRulesPlugin:
    name = "flake8-lint"
    version = __version__

    def __init__(self, tree, filename: str = "<unknown>") -> None:
        self.tree = tree
        self.filename = filename
        self._registry = resolve_registry(include_entry_points=False)

    def run(self):
        source = None
        if self.filename not in (None, "-", "stdin", "<unknown>"):
            try:
                source = Path(self.filename).read_text(encoding="utf-8")
            except OSError:
                source = None

        for violation in check_tree(
            self.tree,
            self.filename,
            source,
            config=LintConfig(),
            registry=self._registry,
        ):
            yield (
                violation.lineno,
                violation.col_offset,
                f"{violation.code} {violation.message}",
                type(self),
            )
