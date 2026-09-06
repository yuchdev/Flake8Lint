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
    _config = LintConfig()

    @classmethod
    def add_options(cls, option_manager) -> None:
        option_manager.add_option(
            "--flake8-lint-no-noqa",
            action="store_true",
            parse_from_config=True,
            default=False,
            help="Disable noqa suppression inside the flake8-lint adapter.",
        )

    @classmethod
    def parse_options(cls, options) -> None:
        select = _extract_x_codes(
            getattr(options, "select", ()),
            getattr(options, "extend_select", ()),
        )
        ignore = _extract_x_codes(
            getattr(options, "ignore", ()),
            getattr(options, "extend_ignore", ()),
        )
        disable_noqa = bool(
            getattr(options, "disable_noqa", False)
            or getattr(options, "flake8_lint_no_noqa", False)
        )
        cls._config = LintConfig(
            select=select,
            ignore=ignore,
            allow_noqa=not disable_noqa,
        )

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
            config=type(self)._config,
            registry=self._registry,
        ):
            yield (
                violation.lineno,
                violation.col_offset,
                f"{violation.code} {violation.message}",
                type(self),
            )


def _extract_x_codes(*groups) -> tuple[str, ...]:
    codes: list[str] = []
    for group in groups:
        for code in group or ():
            upper = str(code).upper()
            if upper.startswith("X") and upper not in codes:
                codes.append(upper)
    return tuple(codes)
