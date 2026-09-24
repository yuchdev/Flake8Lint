"""Authoritative public API and shared engine for flakeforge."""

from __future__ import annotations

import ast
import io
import json
import tokenize
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
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
    :ivar registered_rules: ``(code, description)`` pairs for every rule in the
        resolved registry, ordered by code. Populated by :func:`lint_paths` so
        registry-aware formatters (SARIF) can list all known rules without a
        second registry lookup; defaults to empty for hand-built results. It
        is not part of the base JSON output, but supplies the per-code
        descriptions when statistics are requested.
    """

    violations: tuple[RuleViolation, ...]
    files_checked: int
    registered_rules: tuple[tuple[str, str], ...] = ()

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
        project_root=effective_config.rule_module_root,
    )
    validated_config = (
        validate_config(effective_config, effective_registry.known_codes()) if validate_selectors else effective_config
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
            raise RuleExecutionError(f"Rule {registration.code} from {provider} failed: {exc}") from exc
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
            explicit_registry.register(rule, provider="flakeforge.check_source")
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
        project_root=effective_config.rule_module_root,
    )
    validated_config = validate_config(effective_config, effective_registry.known_codes())
    target_paths = _resolve_target_paths(paths, validated_config)
    if paths:
        file_targets = tuple(path for path in target_paths if path.is_file())
        dir_targets = tuple(path for path in target_paths if path.is_dir())
        files = discover_python_files(dir_targets, config=validated_config)
        if file_targets:
            files = tuple(
                sorted(
                    {
                        *files,
                        *discover_python_files(
                            file_targets,
                            config=validated_config.merge(include=()),
                        ),
                    }
                )
            )
    else:
        files = discover_python_files(target_paths, config=validated_config)
    root_dir = (validated_config.base_dir or Path.cwd()).resolve()
    violations: list[RuleViolation] = []
    for file_path in files:
        display_name = _display_filename(file_path, root_dir)
        file_violations = check_file(
            file_path,
            config=validated_config,
            registry=effective_registry,
        )
        violations.extend(replace(violation, filename=display_name) for violation in file_violations)
    registered_rules = tuple((registration.code, registration.description) for registration in effective_registry.all())
    return LintResult(
        violations=tuple(violations),
        files_checked=len(files),
        registered_rules=registered_rules,
    )


def format_text(result: LintResult, *, statistics: bool = False) -> str:
    """Render *result* as a human-readable text report.

    :param result: The lint outcome to render.
    :param statistics: When true, append a per-code count summary after the
        violation lines (see :func:`_format_statistics_text`). A clean run has
        no violations to summarise, so the summary is omitted entirely and only
        the "no violations found" line is returned.
    :returns: The rendered text report.
    """
    if result.ok:
        return f"Checked {result.files_checked} file(s); no violations found."
    body = "\n".join(
        f"{violation.filename}:{violation.lineno}:{violation.col_offset}: {violation.code} {violation.message}"
        for violation in _sorted_violations(result.violations)
    )
    if not statistics:
        return body
    return f"{body}\n\n{_format_statistics_text(result)}"


def format_json(result: LintResult, *, statistics: bool = False) -> str:
    """Render *result* as a deterministic, indented JSON document.

    The document carries a ``schema_version`` integer so consumers can detect
    incompatible shape changes; existing keys stay unchanged across additive
    revisions.

    :param result: The lint outcome to render.
    :param statistics: When true, add an additive ``statistics`` object mapping
        each violated code to ``{"count", "description"}``. The key appears only
        when requested and leaves every existing key untouched, so
        ``schema_version`` stays ``1`` (an additive optional key cannot break a
        consumer that ignores unknown keys); an empty object is emitted when
        there are no violations.
    :returns: The rendered JSON document.
    """
    payload: dict[str, object] = {
        "schema_version": JSON_SCHEMA_VERSION,
        "ok": result.ok,
        "files_checked": result.files_checked,
        "violations": [violation.__dict__ for violation in _sorted_violations(result.violations)],
    }
    if statistics:
        payload["statistics"] = {
            code: {"count": count, "description": description} for code, count, description in _statistics_rows(result)
        }
    return json.dumps(payload, indent=2, sort_keys=True)


def _statistics_rows(result: LintResult) -> list[tuple[str, int, str]]:
    """Return ``(code, count, description)`` rows for *result*, sorted by code.

    Counts are per violated rule code; descriptions come from
    :attr:`LintResult.registered_rules` (empty string when a code is absent,
    e.g. a hand-built result). Codes with no violations are not listed.
    """
    counts = Counter(violation.code for violation in result.violations)
    descriptions = dict(result.registered_rules)
    return [(code, counts[code], descriptions.get(code, "")) for code in sorted(counts)]


def _format_statistics_text(result: LintResult) -> str:
    """Render the per-code count summary block, e.g. ``X001  3  Bare except``.

    Columns are the rule code left-justified to the widest code, the count
    right-justified to the widest count, and the description, each separated by
    two spaces. Trailing whitespace (an empty description) is stripped.
    """
    rows = _statistics_rows(result)
    code_width = max(len(code) for code, _, _ in rows)
    count_width = max(len(str(count)) for _, count, _ in rows)
    return "\n".join(
        f"{code:<{code_width}}  {count:>{count_width}}  {description}".rstrip() for code, count, description in rows
    )


JSON_SCHEMA_VERSION = 1
"""Schema version stamped into :func:`format_json` output (bumped on breaking changes)."""

SARIF_VERSION = "2.1.0"
"""SARIF specification version emitted by :func:`format_sarif`."""

SARIF_SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
"""``$schema`` URI advertised by :func:`format_sarif` output."""


def _escape_github_data(value: str) -> str:
    """Escape a GitHub workflow-command *message* payload.

    Applies the data-string rules from the GitHub Actions toolkit: ``%`` is
    escaped first (so subsequently introduced ``%`` sequences are not
    double-escaped), then carriage return and newline.
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_github_property(value: str) -> str:
    """Escape a GitHub workflow-command *property* value.

    Property values carry the data-string escapes plus ``:`` and ``,``, which
    otherwise terminate a property or the property list.
    """
    return _escape_github_data(value).replace(":", "%3A").replace(",", "%2C")


def format_github(result: LintResult) -> str:
    """Render *result* as GitHub Actions ``::error`` workflow commands.

    Emits one annotation per violation, ordered by :func:`_sorted_violations`
    (plan contract C9). Columns are 1-based (the engine stores a 0-based
    ``col_offset``). An empty result renders as the empty string, so the CLI
    prints nothing for a clean run rather than a stray annotation.

    :param result: The lint outcome to render.
    :returns: Newline-separated workflow commands, or ``""`` when clean.
    """
    lines = [
        f"::error file={_escape_github_property(violation.filename)},"
        f"line={violation.lineno},col={violation.col_offset + 1},"
        f"title={_escape_github_property(violation.code)}::"
        f"{_escape_github_data(violation.message)}"
        for violation in _sorted_violations(result.violations)
    ]
    return "\n".join(lines)


def _sarif_uri(filename: str) -> str:
    """Return *filename* as a forward-slash SARIF ``artifactLocation`` URI.

    :func:`lint_paths` display names are already ``base_dir``-relative POSIX
    paths (plan contract C6); the backslash replacement only matters for the
    absolute-path fallback on Windows, keeping the URI portable.
    """
    return filename.replace("\\", "/")


def format_sarif(result: LintResult) -> str:
    """Render *result* as a SARIF 2.1.0 document (built with ``json`` only, C8).

    The single run advertises the ``flakeforge`` driver and its package version,
    lists one ``rules[]`` entry per registered code (from
    :attr:`LintResult.registered_rules`), and one ``results[]`` entry per
    violation with a 1-based region. Output is deterministic: results follow the
    C9 ordering and rules keep the registry's code order, with ``sort_keys``
    stabilising object-key order.

    :param result: The lint outcome to render.
    :returns: An indented SARIF 2.1.0 JSON document.
    """
    # Imported lazily to avoid an import cycle: the package ``__init__`` imports
    # this module, so ``__version__`` is not yet bound at api import time.
    from . import __version__  # noqa: X006

    driver_rules = [
        {"id": code, "shortDescription": {"text": description}} for code, description in result.registered_rules
    ]
    results = [
        {
            "ruleId": violation.code,
            "level": "error",
            "message": {"text": violation.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": _sarif_uri(violation.filename)},
                        "region": {
                            "startLine": violation.lineno,
                            "startColumn": violation.col_offset + 1,
                        },
                    }
                }
            ],
        }
        for violation in _sorted_violations(result.violations)
    ]
    document = {
        "$schema": SARIF_SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "flakeforge",
                        "version": __version__,
                        "rules": driver_rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True)


FORMATTERS: dict[str, Callable[[LintResult], str]] = {
    "text": format_text,
    "json": format_json,
    "github": format_github,
    "sarif": format_sarif,
}
"""Single source of truth mapping each output-format name to its renderer.

The CLI ``--output-format`` choices and :func:`validate_output_format` both read
this table, so registering a formatter here is enough to expose it everywhere
(04.0 extends it with CI-native formats).
"""

KNOWN_OUTPUT_FORMATS: tuple[str, ...] = tuple(FORMATTERS)
"""Registered output-format names, derived from :data:`FORMATTERS` (kept for API stability)."""

STATISTICS_FORMATS: tuple[str, ...] = ("text", "json")
"""Formats that render a ``--statistics`` summary; ``github``/``sarif`` ignore it.

:func:`format_result` only threads ``statistics`` into these formatters; the CLI
consults this table to warn (on stderr) when ``--statistics`` is set for a format
that drops it. The engine never prints -- surfacing the warning is the CLI's job.
"""


def validate_output_format(output_format: str) -> str:
    """Return *output_format* if it names a known formatter.

    :param output_format: The requested formatter name.
    :returns: The validated formatter name, unchanged.
    :raises ValueError: If *output_format* is not a registered formatter; the
        CLI maps this to exit code ``2`` (plan contract C1).
    """
    if output_format not in FORMATTERS:
        known = ", ".join(KNOWN_OUTPUT_FORMATS)
        raise ValueError(f"Unknown output format {output_format!r}; choose from {known}")
    return output_format


def format_result(result: LintResult, output_format: str, *, statistics: bool = False) -> str:
    """Render *result* using the formatter named by *output_format*.

    ``statistics`` is a rendering concern threaded here rather than through the
    :data:`FORMATTERS` registry signature, which stays ``Callable[[LintResult],
    str]``. It is applied only for the formats in :data:`STATISTICS_FORMATS`
    (``text``/``json``); ``github``/``sarif`` silently ignore it (the CLI emits
    the user-facing warning).

    :param result: The lint outcome to render.
    :param output_format: Name of a registered formatter.
    :param statistics: When true, request a per-code count summary from formats
        that support one.
    :returns: The rendered report text.
    :raises ValueError: If *output_format* is not a registered formatter.
    """
    validated = validate_output_format(output_format)
    formatter = FORMATTERS[validated]
    if statistics and validated in STATISTICS_FORMATS:
        return formatter(result, statistics=True)  # type: ignore[call-arg]
    return formatter(result)


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
            resolved.append(candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve())
        return tuple(resolved)
    if config.include:
        return _include_traversal_roots(config.include, root_dir) or (root_dir,)
    defaults = tuple(candidate for candidate in (root_dir / "src", root_dir / "tests") if candidate.exists())
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
    """Return *path* relative to the config ``base_dir``, else the cwd, else raw.

    The config ``base_dir`` (*root_dir*) is tried first (plan contract C6) so a
    ``--config`` run prints identical, base-relative names whatever the process
    cwd is -- this fixes G7, where an ancestor cwd previously produced a long
    ``project/pkg/m.py`` display instead of ``pkg/m.py``. The cwd is a secondary
    anchor so sibling ``include`` roots such as ``../src`` still render cleanly,
    and the raw (absolute) path is the last-resort fallback for a file that lies
    under neither anchor.
    """
    resolved = path.resolve()
    for base in (root_dir, Path.cwd().resolve()):
        if resolved.is_relative_to(base):
            return resolved.relative_to(base).as_posix()
    return str(path)
