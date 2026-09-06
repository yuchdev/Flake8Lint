"""Authoritative public API and shared engine for flake8-lint."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import LintConfig
from .discovery import discover_python_files

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2


@dataclass(frozen=True)
class RuleViolation:
    filename: str
    lineno: int
    col_offset: int
    code: str
    message: str


@dataclass(frozen=True)
class LintResult:
    violations: tuple[RuleViolation, ...]
    files_checked: int

    @property
    def ok(self) -> bool:
        return not self.violations


@dataclass(frozen=True)
class RuleContext:
    tree: ast.AST
    filename: str
    source: str | None


class Rule(Protocol):
    code: str
    description: str

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        ...


class RuleExecutionError(RuntimeError):
    """Raised when a rule provider fails during execution."""


def check_tree(
    tree: ast.AST,
    filename: str,
    source: str | None = None,
    *,
    config: LintConfig | None = None,
    registry=None,
) -> tuple[RuleViolation, ...]:
    from .registry import resolve_registry

    effective_config = config or LintConfig()
    effective_registry = registry or resolve_registry(
        rule_modules=effective_config.rule_modules,
        include_entry_points=True,
    )
    context = RuleContext(tree=tree, filename=filename, source=source)
    violations: list[RuleViolation] = []

    for registration in effective_registry.enabled_rules():
        if not _is_rule_enabled(registration.code, effective_config):
            continue
        try:
            emitted = tuple(registration.rule.check(context))
        except Exception as exc:  # pragma: no cover - defensive surface
            provider = registration.provider or "<unknown provider>"
            raise RuleExecutionError(
                f"Rule {registration.code} from {provider} failed: {exc}"
            ) from exc
        for violation in emitted:
            if _is_noqa_suppressed(violation, context.source, effective_config):
                continue
            violations.append(violation)

    return tuple(violations)


def check_file(
    path: str | Path,
    *,
    config: LintConfig | None = None,
    registry=None,
) -> tuple[RuleViolation, ...]:
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    return check_tree(tree, str(file_path), source, config=config, registry=registry)


def lint_paths(
    paths: Sequence[str | Path] | None = None,
    *,
    config: LintConfig | None = None,
    registry=None,
) -> LintResult:
    from .registry import resolve_registry

    effective_config = config or LintConfig()
    effective_registry = registry or resolve_registry(
        rule_modules=effective_config.rule_modules,
        include_entry_points=True,
    )
    target_paths = tuple(paths or (Path.cwd(),))
    files = discover_python_files(target_paths, config=effective_config)
    violations: list[RuleViolation] = []
    for file_path in files:
        violations.extend(
            check_file(
                file_path,
                config=effective_config,
                registry=effective_registry,
            )
        )
    return LintResult(violations=tuple(violations), files_checked=len(files))


def format_text(result: LintResult) -> str:
    if result.ok:
        return f"Checked {result.files_checked} file(s); no violations found."
    return "\n".join(
        f"{violation.filename}:{violation.lineno}:{violation.col_offset}: "
        f"{violation.code} {violation.message}"
        for violation in result.violations
    )


def format_json(result: LintResult) -> str:
    payload = {
        "ok": result.ok,
        "files_checked": result.files_checked,
        "violations": [violation.__dict__ for violation in result.violations],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _is_rule_enabled(code: str, config: LintConfig) -> bool:
    if config.select and code not in config.select:
        return False
    if code in config.ignore:
        return False
    return True


def _is_noqa_suppressed(
    violation: RuleViolation,
    source: str | None,
    config: LintConfig,
) -> bool:
    if not config.allow_noqa or source is None:
        return False
    if config.noqa_allowed and violation.code not in config.noqa_allowed:
        return False
    if violation.code in config.noqa_forbidden:
        return False

    lines = source.splitlines()
    index = violation.lineno - 1
    if index < 0 or index >= len(lines):
        return False

    codes = _parse_noqa_codes(lines[index])
    if codes is None:
        return False
    if not codes:
        return True
    return violation.code in codes


def _parse_noqa_codes(line: str) -> frozenset[str] | None:
    marker = "#"
    if marker not in line:
        return None
    comment = line.split(marker, 1)[1].strip()
    lowered = comment.lower()
    if not lowered.startswith("noqa"):
        return None
    if ":" not in comment:
        return frozenset()

    _, raw_codes = comment.split(":", 1)
    cleaned_codes: list[str] = []
    for chunk in raw_codes.split(","):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        cleaned_codes.append(cleaned.split()[0].upper())
    return frozenset(cleaned_codes)
