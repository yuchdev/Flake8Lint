"""Authoritative public API and shared engine for flake8-lint."""

from __future__ import annotations

import ast
import io
import json
import tokenize
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Protocol, Union

from .config import LintConfig, validate_config
from .discovery import discover_python_files, path_matches_any
from .registry import RuleRegistry, resolve_registry

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2


@dataclass(frozen=True)
class RuleViolation:
    """A single rule violation located in a source file.

    :ivar filename: File the violation was found in.
    :ivar lineno: 1-based line number of the violation.
    :ivar col_offset: 0-based column offset of the violation.
    :ivar code: Rule code that produced the violation.
    :ivar message: Human-readable description of the violation.
    """

    filename: str
    lineno: int
    col_offset: int
    code: str
    message: str


@dataclass(frozen=True)
class LintResult:
    """Aggregate outcome of linting one or more files.

    :ivar violations: All violations found, in emission order.
    :ivar files_checked: Number of files that were linted.
    """

    violations: tuple[RuleViolation, ...]
    files_checked: int

    @property
    def ok(self) -> bool:
        """Whether the run produced no violations."""
        return not self.violations


@dataclass(frozen=True)
class RuleContext:
    """Inputs handed to each rule for a single module.

    :ivar tree: Parsed AST of the module under analysis.
    :ivar filename: Display name of the module being linted.
    :ivar source: Original source text, when available, for line inspection.
    """

    tree: ast.AST
    filename: str
    source: Optional[str]


class Rule(Protocol):
    """Structural type implemented by every runnable rule.

    :ivar code: The rule's unique code.
    :ivar description: Human-readable summary of the rule.
    """

    code: str
    description: str

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        """Yield the violations this rule finds in *context*."""
        ...


class RuleExecutionError(RuntimeError):
    """Raised when a rule provider fails during execution."""


def check_tree(
    tree: ast.AST,
    filename: str,
    source: Optional[str] = None,
    *,
    apply_noqa: bool = True,
    validate_selectors: bool = True,
    config: Optional[LintConfig] = None,
    registry=None,
) -> tuple[RuleViolation, ...]:
    """Run the resolved rule registry over a parsed module.

    Callers may pass a pre-resolved *registry* to control provider loading and
    avoid repeated discovery work across multiple files.
    """

    effective_config = config or LintConfig()
    effective_registry = registry or resolve_registry(
        rule_modules=effective_config.rule_modules,
        include_entry_points=True,
    )
    validated_config = (
        validate_config(effective_config, effective_registry.known_codes())
        if validate_selectors
        else effective_config
    )
    context = RuleContext(tree=tree, filename=filename, source=source)
    violations: list[RuleViolation] = []

    for registration in effective_registry.enabled_rules():
        if not _is_rule_enabled(registration.code, validated_config):
            continue
        try:
            emitted = tuple(registration.rule.check(context))
        except (
            AttributeError,
            TypeError,
            ValueError,
            KeyError,
            IndexError,
            RuntimeError,
        ) as exc:  # pragma: no cover - defensive surface
            provider = registration.provider or "<unknown provider>"
            raise RuleExecutionError(
                f"Rule {registration.code} from {provider} failed: {exc}"
            ) from exc
        for violation in emitted:
            if _is_noqa_suppressed(
                violation,
                context.source,
                validated_config,
                apply_noqa=apply_noqa,
            ):
                continue
            violations.append(violation)

    return tuple(violations)


def check_file(
    path: Union[str, Path],
    *,
    apply_noqa: bool = True,
    validate_selectors: bool = True,
    config: Optional[LintConfig] = None,
    registry=None,
) -> tuple[RuleViolation, ...]:
    """Parse a Python file and run the resolved registry against it.

    Callers may pass a pre-resolved *registry* to reuse provider discovery
    across repeated file checks.
    """
    file_path = Path(path)
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    return check_tree(
        tree,
        str(file_path),
        source,
        apply_noqa=apply_noqa,
        validate_selectors=validate_selectors,
        config=config,
        registry=registry,
    )


def check_source(
    source: str,
    *,
    filename: str = "<string>",
    apply_noqa: bool = True,
    validate_selectors: bool = True,
    config: Optional[LintConfig] = None,
    registry=None,
    rules: Optional[Sequence[Rule]] = None,
) -> tuple[RuleViolation, ...]:
    """Parse source text and lint it with either an explicit registry or rules."""
    tree = ast.parse(source, filename=filename)
    effective_registry = registry
    if effective_registry is None and rules is not None:
        explicit_registry = RuleRegistry()
        for rule in rules:
            explicit_registry.register(rule, provider="flake8_lint.check_source")
        effective_registry = explicit_registry
    return check_tree(
        tree,
        filename,
        source,
        apply_noqa=apply_noqa,
        validate_selectors=validate_selectors,
        config=config,
        registry=effective_registry,
    )


def lint_paths(
    paths: Optional[Sequence[Union[str, Path]]] = None,
    *,
    config: Optional[LintConfig] = None,
    registry=None,
) -> LintResult:
    """Discover Python files under *paths* and lint them.

    Callers may pass a pre-resolved *registry* when linting many files to avoid
    repeated provider-loading overhead.
    """

    effective_config = config or LintConfig()
    effective_registry = registry or resolve_registry(
        rule_modules=effective_config.rule_modules,
        include_entry_points=True,
    )
    validated_config = validate_config(effective_config, effective_registry.known_codes())
    target_paths = _resolve_target_paths(paths, validated_config)
    discovery_config = validated_config.merge(include=()) if paths else validated_config
    files = discover_python_files(target_paths, config=discovery_config)
    root_dir = (validated_config.base_dir or Path.cwd()).resolve()
    violations: list[RuleViolation] = []
    for file_path in files:
        display_name = _display_filename(file_path, root_dir)
        file_violations = check_file(
            file_path,
            config=validated_config,
            registry=effective_registry,
        )
        violations.extend(
            replace(violation, filename=display_name) for violation in file_violations
        )
    return LintResult(violations=tuple(violations), files_checked=len(files))


def format_text(result: LintResult) -> str:
    """Render *result* as a human-readable text report."""
    if result.ok:
        return f"Checked {result.files_checked} file(s); no violations found."
    return "\n".join(
        f"{violation.filename}:{violation.lineno}:{violation.col_offset}: "
        f"{violation.code} {violation.message}"
        for violation in _sorted_violations(result.violations)
    )


def format_json(result: LintResult) -> str:
    """Render *result* as a deterministic, indented JSON document."""
    payload = {
        "ok": result.ok,
        "files_checked": result.files_checked,
        "violations": [violation.__dict__ for violation in _sorted_violations(result.violations)],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _is_rule_enabled(code: str, config: LintConfig) -> bool:
    """Return whether *code* survives the config's select/ignore filters."""
    if config.select and not _matches_code_prefix(code, config.select):
        return False
    if _matches_code_prefix(code, config.ignore):
        return False
    return True


def _is_noqa_suppressed(
    violation: RuleViolation,
    source: Optional[str],
    config: LintConfig,
    *,
    apply_noqa: bool,
) -> bool:
    """Return whether *violation* is suppressed by a ``# noqa`` on its line."""
    if not apply_noqa or not config.allow_noqa or source is None:
        return False
    if not _path_allows_noqa(violation.filename, config):
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
    return _matches_code_prefix(violation.code, tuple(codes))


def _path_allows_noqa(filename: str, config: LintConfig) -> bool:
    """Return whether ``# noqa`` is permitted for *filename* under *config*."""
    root_dir = config.base_dir or Path.cwd()
    if path_matches_any(filename, config.noqa_forbidden, root_dir):
        return False
    if config.noqa_allowed and not path_matches_any(filename, config.noqa_allowed, root_dir):
        return False
    return True


def _parse_noqa_codes(line: str) -> Optional[frozenset[str]]:
    """Parse the codes from a ``# noqa`` comment on *line*.

    :returns: ``None`` when the line carries no ``noqa`` comment, an empty set
        for a bare ``# noqa`` (suppress everything), or the specific codes.
    """
    comment = _extract_comment(line)
    if comment is None:
        return None
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


def _extract_comment(line: str) -> Optional[str]:
    """Return the trailing comment text on *line*, or ``None`` if absent."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(line).readline):
            if token.type == tokenize.COMMENT:
                return token.string.removeprefix("#").strip()
    except tokenize.TokenError:
        # A single line that cannot be tokenised in isolation (e.g. an
        # unterminated string) exposes no recognisable comment.
        no_comment: Optional[str] = None
        return no_comment
    return None


def _matches_code_prefix(code: str, prefixes: Sequence[str]) -> bool:
    """Return whether *code* starts with any entry in *prefixes*."""
    return any(code.startswith(prefix) for prefix in prefixes)


def _sorted_violations(
    violations: Sequence[RuleViolation],
) -> list[RuleViolation]:
    """Return *violations* sorted by location, code, and message."""
    return sorted(
        violations,
        key=lambda violation: (
            violation.filename,
            violation.lineno,
            violation.col_offset,
            violation.code,
            violation.message,
        ),
    )


def _resolve_target_paths(
    paths: Optional[Sequence[Union[str, Path]]],
    config: LintConfig,
) -> tuple[Path, ...]:
    """Resolve the concrete directories/files to scan for a lint run.

    Explicit *paths* win; otherwise the config's ``include`` roots are used, and
    finally ``src``/``tests`` (or the base directory) as defaults.
    """
    root_dir = (config.base_dir or Path.cwd()).resolve()
    if paths:
        resolved: list[Path] = []
        for raw_path in paths:
            candidate = Path(raw_path)
            resolved.append(
                candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
            )
        return tuple(resolved)
    if config.include:
        return _include_traversal_roots(config.include, root_dir) or (root_dir,)
    defaults = tuple(
        candidate for candidate in (root_dir / "src", root_dir / "tests") if candidate.exists()
    )
    return defaults or (root_dir,)


def _include_traversal_roots(include: Sequence[str], root_dir: Path) -> tuple[Path, ...]:
    """Derive existing traversal roots from the config's include patterns."""
    roots: list[Path] = []
    for pattern in include:
        if not pattern.strip():
            continue
        root = _safe_traversal_root(pattern, root_dir)
        if root.exists() and root not in roots:
            roots.append(root)
    return tuple(roots)


def _safe_traversal_root(pattern: str, root_dir: Path) -> Path:
    """Return the fixed directory prefix of *pattern* before any glob wildcard."""
    parts = Path(pattern).parts
    root = Path(parts[0]) if parts and Path(parts[0]).is_absolute() else root_dir
    prefix: list[str] = []
    for part in parts:
        if any(character in part for character in "*?["):
            break
        prefix.append(part)
    if not prefix:
        return root
    if Path(prefix[0]).is_absolute():
        return Path(*prefix).resolve()
    return (root_dir / Path(*prefix)).resolve()


def _display_filename(path: Path, root_dir: Path) -> str:
    """Return *path* relative to the cwd or *root_dir*, else its raw string."""
    resolved = path.resolve()
    for base in (Path.cwd().resolve(), root_dir):
        if resolved.is_relative_to(base):
            return resolved.relative_to(base).as_posix()
    return str(path)
