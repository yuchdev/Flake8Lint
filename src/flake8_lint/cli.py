"""Command-line interface for flake8-lint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .api import EXIT_ERROR, EXIT_OK, EXIT_VIOLATIONS, format_json, format_text, lint_paths
from .config import LintConfig, load_config, validate_config
from .registry import resolve_registry


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser and its ``check`` subcommand."""
    parser = argparse.ArgumentParser(prog="flake8-lint")
    parser.add_argument("--version", action="store_true", help="Show package version and exit")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Lint one or more files or directories")
    check.add_argument("paths", nargs="*")
    check.add_argument("--config", help="Path to pyproject.toml or flake8_lint.toml")
    check.add_argument("--select", action="append", default=[])
    check.add_argument("--ignore", action="append", default=[])
    check.add_argument("--no-noqa", action="store_true", help="Disable noqa suppression")
    check.add_argument("--rule-module", action="append", default=[])
    check.add_argument(
        "--no-rule-plugins",
        action="store_true",
        help="Disable installed flake8_lint.rules entry-point providers",
    )
    check.add_argument("--output-format", choices=("text", "json"), default="text")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the ``flake8-lint`` CLI and return a process exit code.

    :param argv: Optional argument vector; defaults to ``sys.argv`` when omitted.
    :returns: ``EXIT_OK`` when clean, ``EXIT_VIOLATIONS`` when violations are
        found, or ``EXIT_ERROR`` when the invocation fails.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"flake8-lint {__version__}")
        return EXIT_OK
    if args.command != "check":
        parser.print_help()
        return EXIT_ERROR

    try:
        config = _build_cli_config(args)
        registry = resolve_registry(
            rule_modules=config.rule_modules,
            include_entry_points=not args.no_rule_plugins,
        )
        config = validate_config(config, registry.known_codes())
        _emit_warnings(config)
        result = lint_paths(
            tuple(Path(path) for path in args.paths),
            config=config,
            registry=registry,
        )
    except (OSError, ValueError, RuntimeError, SyntaxError) as exc:
        print(f"flake8-lint: {exc}", file=sys.stderr)
        return EXIT_ERROR

    output = format_json(result) if args.output_format == "json" else format_text(result)
    print(output)
    return EXIT_OK if result.ok else EXIT_VIOLATIONS


def _build_cli_config(args: argparse.Namespace) -> LintConfig:
    """Load the on-disk config and overlay CLI overrides onto it."""
    if args.config:
        config = load_config(args.config, cwd=Path.cwd())
    else:
        config = load_config(cwd=Path.cwd())
    select = _split_codes(args.select)
    ignore = _split_codes(args.ignore)
    rule_modules = tuple(args.rule_module)
    return config.merge(
        select=select if select else None,
        ignore=ignore if ignore else None,
        allow_noqa=False if args.no_noqa else None,
        rule_modules=_merge_unique(config.rule_modules, rule_modules) if rule_modules else None,
    )


def _split_codes(values: list[str]) -> tuple[str, ...]:
    """Split comma-separated ``--select``/``--ignore`` values into codes."""
    parsed: list[str] = []
    for value in values:
        parsed.extend(chunk.strip().upper() for chunk in value.split(",") if chunk.strip())
    return tuple(parsed)


def _merge_unique(existing: tuple[str, ...], extra: tuple[str, ...]) -> tuple[str, ...]:
    """Append *extra* entries to *existing*, preserving order and uniqueness."""
    merged = list(existing)
    for value in extra:
        if value not in merged:
            merged.append(value)
    return tuple(merged)


def _emit_warnings(config: LintConfig):
    """Print any accumulated configuration warnings to stderr."""
    for warning in config.warnings:
        print(f"flake8-lint: {warning}", file=sys.stderr)
