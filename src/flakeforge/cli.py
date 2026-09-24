"""Command-line interface for flakeforge."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .api import (
    EXIT_ERROR,
    EXIT_OK,
    EXIT_VIOLATIONS,
    KNOWN_OUTPUT_FORMATS,
    format_result,
    lint_paths,
    validate_output_format,
)
from .config import LintConfig, discovery_anchor, isolated_config, load_config, validate_config
from .registry import resolve_registry


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser and its ``check`` subcommand."""
    parser = argparse.ArgumentParser(prog="flakeforge")
    parser.add_argument("--version", action="store_true", help="Show package version and exit")
    subparsers = parser.add_subparsers(dest="command")

    check = subparsers.add_parser("check", help="Lint one or more files or directories")
    check.add_argument("paths", nargs="*")
    config_source = check.add_mutually_exclusive_group()
    config_source.add_argument("--config", help="Path to pyproject.toml or flakeforge.toml")
    config_source.add_argument(
        "--no-config",
        action="store_true",
        help="Skip config discovery; use built-in defaults plus CLI flags only",
    )
    check.add_argument("--select", action="append", default=[])
    check.add_argument("--ignore", action="append", default=[])
    check.add_argument("--include", action="append", default=[])
    check.add_argument("--exclude", action="append", default=[])
    check.add_argument(
        "--noqa",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Honour (or, with --no-noqa, disable) # noqa suppression",
    )
    check.add_argument("--rule-module", action="append", default=[])
    check.add_argument(
        "--rule-plugins",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Load (or, with --no-rule-plugins, skip) installed flakeforge.rules providers",
    )
    check.add_argument("--output-format", choices=KNOWN_OUTPUT_FORMATS, default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the ``flakeforge`` CLI and return a process exit code.

    :param argv: Optional argument vector; defaults to ``sys.argv`` when omitted.
    :returns: ``EXIT_OK`` when clean, ``EXIT_VIOLATIONS`` when violations are
        found, or ``EXIT_ERROR`` when the invocation fails.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"flakeforge {__version__}")
        return EXIT_OK
    if args.command != "check":
        parser.print_help()
        return EXIT_ERROR

    missing = [path for path in args.paths if not Path(path).exists()]
    if missing:
        for path in missing:
            print(f"flakeforge: path does not exist: {path}", file=sys.stderr)
        return EXIT_ERROR

    try:
        config = _build_cli_config(args)
        validate_output_format(config.output_format)
        registry = resolve_registry(
            rule_modules=config.rule_modules,
            include_entry_points=config.rule_plugins,
            project_root=config.rule_module_root,
        )
        config = validate_config(config, registry.known_codes())
        _emit_warnings(config)
        result = lint_paths(
            tuple(Path(path) for path in args.paths),
            config=config,
            registry=registry,
        )
        output = format_result(result, config.output_format)
    except (OSError, ValueError, RuntimeError, SyntaxError) as exc:
        print(f"flakeforge: {exc}", file=sys.stderr)
        return EXIT_ERROR

    print(output)
    return EXIT_OK if result.ok else EXIT_VIOLATIONS


def _build_cli_config(args: argparse.Namespace) -> LintConfig:
    """Load the on-disk config and overlay CLI overrides onto it."""
    if args.config:
        config = load_config(args.config, cwd=Path.cwd())
    elif args.no_config:
        config = isolated_config(args.paths, cwd=Path.cwd())
    else:
        anchor = discovery_anchor(args.paths, cwd=Path.cwd())
        config = load_config(cwd=anchor)
    select = _split_codes(args.select)
    ignore = _split_codes(args.ignore)
    include = _split_patterns(args.include)
    exclude = _split_patterns(args.exclude)
    rule_modules = tuple(args.rule_module)
    return config.merge(
        include=include if include else None,
        exclude=exclude if exclude else None,
        select=select if select else None,
        ignore=ignore if ignore else None,
        allow_noqa=args.noqa,
        rule_modules=_merge_unique(config.rule_modules, rule_modules) if rule_modules else None,
        rule_plugins=args.rule_plugins,
        output_format=args.output_format,
    )


def _split_codes(values: list[str]) -> tuple[str, ...]:
    """Split comma-separated ``--select``/``--ignore`` values into codes."""
    parsed: list[str] = []
    for value in values:
        parsed.extend(chunk.strip().upper() for chunk in value.split(",") if chunk.strip())
    return tuple(parsed)


def _split_patterns(values: list[str]) -> tuple[str, ...]:
    """Split comma-separated ``--include``/``--exclude`` values into patterns.

    Mirrors :func:`_split_codes` but preserves case, since these are path
    globs rather than rule codes.
    """
    parsed: list[str] = []
    for value in values:
        parsed.extend(chunk.strip() for chunk in value.split(",") if chunk.strip())
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
        print(f"flakeforge: {warning}", file=sys.stderr)
