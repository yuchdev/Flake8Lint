"""Command-line interface for flake8-lint."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .api import EXIT_ERROR, EXIT_OK, EXIT_VIOLATIONS, format_json, format_text, lint_paths
from .config import LintConfig, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flake8-lint")
    parser.add_argument("--version", action="store_true", help="Show package version and exit")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Lint one or more files or directories")
    check.add_argument("paths", nargs="*", default=["."])
    check.add_argument("--config", help="Path to pyproject.toml or flake8_lint.toml")
    check.add_argument("--select", action="append", default=[])
    check.add_argument("--ignore", action="append", default=[])
    check.add_argument("--no-noqa", action="store_true", help="Disable noqa suppression")
    check.add_argument("--rule-module", action="append", default=[])
    check.add_argument("--output-format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return EXIT_OK
    if args.command != "check":
        parser.print_help()
        return EXIT_ERROR

    try:
        config = _build_cli_config(args)
        result = lint_paths(tuple(Path(path) for path in args.paths), config=config)
    except Exception as exc:
        print(f"flake8-lint: {exc}")
        return EXIT_ERROR

    output = format_json(result) if args.output_format == "json" else format_text(result)
    print(output)
    return EXIT_OK if result.ok else EXIT_VIOLATIONS


def _build_cli_config(args: argparse.Namespace) -> LintConfig:
    config = load_config(args.config) if args.config else load_config()
    select = _split_codes(args.select)
    ignore = _split_codes(args.ignore)
    rule_modules = tuple(args.rule_module)
    return config.merge(
        select=select or None,
        ignore=ignore or None,
        allow_noqa=False if args.no_noqa else None,
        rule_modules=rule_modules or None,
    )


def _split_codes(values: list[str]) -> tuple[str, ...]:
    parsed: list[str] = []
    for value in values:
        parsed.extend(chunk.strip().upper() for chunk in value.split(",") if chunk.strip())
    return tuple(parsed)
