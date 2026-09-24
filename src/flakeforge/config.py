"""Typed configuration loading for flakeforge."""

from __future__ import annotations

import difflib
import os
import tomllib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Optional, Union

LEGACY_SECTION_WARNING = "[tool.flake8_lint] is deprecated; rename it to [tool.flakeforge]."


class ConfigValidationError(ValueError):
    """Raised when a config file or invocation supplies invalid settings."""


@dataclass(frozen=True)
class LintConfig:
    """Immutable, fully-resolved linter configuration.

    :ivar include: Glob patterns limiting which files are linted.
    :ivar exclude: Glob patterns excluding files from linting.
    :ivar select: Rule-code prefixes to enable; empty means all rules.
    :ivar ignore: Rule-code prefixes to disable.
    :ivar allow_noqa: Whether ``# noqa`` suppression is honoured.
    :ivar noqa_allowed: Path patterns where ``# noqa`` is permitted (file-only).
    :ivar noqa_forbidden: Path patterns where ``# noqa`` is rejected (file-only).
    :ivar rule_modules: Importable modules contributing extra rules.
    :ivar rule_plugins: Whether installed ``flakeforge.rules`` entry-point
        providers are loaded.
    :ivar output_format: Name of the formatter used to render results.
    :ivar statistics: Whether to append a per-code count summary to the output.
    :ivar base_dir: Directory patterns are resolved against; excluded from equality.
    :ivar config_path: Path the config was loaded from; excluded from equality.
    :ivar legacy_mode: Whether a deprecated config section was used.
    :ivar warnings: Accumulated non-fatal configuration warnings.
    """

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    select: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    allow_noqa: bool = True
    noqa_allowed: tuple[str, ...] = ()
    noqa_forbidden: tuple[str, ...] = ()
    rule_modules: tuple[str, ...] = ()
    rule_plugins: bool = True
    output_format: str = "text"
    statistics: bool = False
    base_dir: Optional[Path] = field(default=None, compare=False)
    config_path: Optional[Path] = field(default=None, compare=False)
    legacy_mode: bool = field(default=False, compare=False)
    warnings: tuple[str, ...] = field(default=(), compare=False)

    @classmethod
    def from_mapping(
        cls,
        data: Optional[dict[str, Any]],
        *,
        base_dir: Optional[Path] = None,
        config_path: Optional[Path] = None,
        legacy_mode: bool = False,
        warnings: Iterable[str] = (),
        source: Optional[str] = None,
    ) -> LintConfig:
        """Build a :class:`LintConfig` from a parsed TOML mapping.

        Both config surfaces (``flakeforge.toml`` and ``[tool.flakeforge]``) run
        through this one method, which is driven by :data:`_CONFIG_SCHEMA` (plan
        contract C5). Unknown keys raise :class:`ConfigValidationError` with a
        ``difflib`` did-you-mean hint, except in *legacy_mode* where they are
        appended to ``warnings`` instead. Type errors carry the same *source*
        prefix. This method never prints; the CLI surfaces warnings.

        :param data: Raw config table, or ``None`` for an empty configuration.
        :param base_dir: Directory patterns are resolved against.
        :param config_path: Path the config originated from.
        :param legacy_mode: Whether the data came from a deprecated section.
        :param warnings: Pre-existing warnings to carry forward.
        :param source: Human-readable label for the config file/section, used to
            prefix validation errors (e.g. ``flakeforge.toml`` or
            ``pyproject.toml [tool.flakeforge]``); ``None`` yields no prefix.
        :returns: A validated, immutable configuration instance.
        :raises ConfigValidationError: On an unknown key (outside legacy mode) or
            a value of the wrong type.
        """
        payload = data or {}
        prefix = f"{source}: " if source else ""
        accumulated = list(warnings)

        for key in payload:
            if key in _CONFIG_SCHEMA:
                continue
            if legacy_mode:
                accumulated.append(f"{prefix}unknown key {key!r}")
                continue
            match = difflib.get_close_matches(key, list(_CONFIG_SCHEMA), n=1)
            hint = f" (did you mean {match[0]!r}?)" if match else ""
            raise ConfigValidationError(f"{prefix}unknown key {key!r}{hint}")

        values: dict[str, Any] = {}
        for key, (coerce, default) in _CONFIG_SCHEMA.items():
            try:
                values[key] = coerce(payload.get(key, default), field_name=key)
            except ConfigValidationError as exc:
                raise ConfigValidationError(f"{prefix}{exc}") from exc

        return cls(
            **values,
            base_dir=base_dir,
            config_path=config_path,
            legacy_mode=legacy_mode,
            warnings=tuple(accumulated),
        )

    @property
    def rule_module_root(self) -> Optional[Path]:
        """Directory to put on ``sys.path`` while project ``rule_modules`` load.

        Only a config actually loaded from a file vouches for its directory
        (plan contract C7). Defaults-only configs -- ``--no-config`` or no
        config file found -- return ``None``, so an explicit ``--rule-module``
        resolves from the existing ``sys.path`` and the target directory is
        never trusted implicitly.
        """
        return self.base_dir if self.config_path is not None else None

    def merge(
        self,
        *,
        include: Optional[tuple[str, ...]] = None,
        exclude: Optional[tuple[str, ...]] = None,
        select: Optional[tuple[str, ...]] = None,
        ignore: Optional[tuple[str, ...]] = None,
        allow_noqa: Optional[bool] = None,
        noqa_allowed: Optional[tuple[str, ...]] = None,
        noqa_forbidden: Optional[tuple[str, ...]] = None,
        rule_modules: Optional[tuple[str, ...]] = None,
        rule_plugins: Optional[bool] = None,
        output_format: Optional[str] = None,
        statistics: Optional[bool] = None,
        warnings: Optional[tuple[str, ...]] = None,
    ) -> LintConfig:
        """Return a copy with the supplied (non-``None``) fields overridden.

        ``select`` and ``ignore`` values are upper-cased when provided; every
        other field is copied verbatim, and ``None`` leaves the field unchanged.

        :returns: A new configuration reflecting the requested overrides.
        """
        return replace(
            self,
            include=self.include if include is None else include,
            exclude=self.exclude if exclude is None else exclude,
            select=self.select if select is None else _normalize_codes(select),
            ignore=self.ignore if ignore is None else _normalize_codes(ignore),
            allow_noqa=self.allow_noqa if allow_noqa is None else allow_noqa,
            noqa_allowed=self.noqa_allowed if noqa_allowed is None else noqa_allowed,
            noqa_forbidden=(self.noqa_forbidden if noqa_forbidden is None else noqa_forbidden),
            rule_modules=self.rule_modules if rule_modules is None else rule_modules,
            rule_plugins=self.rule_plugins if rule_plugins is None else rule_plugins,
            output_format=self.output_format if output_format is None else output_format,
            statistics=self.statistics if statistics is None else statistics,
            warnings=self.warnings if warnings is None else warnings,
        )


def discovery_anchor(
    paths: Sequence[Union[str, Path]],
    *,
    cwd: Union[str, Path],
) -> Path:
    """Resolve the directory config discovery should walk upward from.

    Implements the *discovery anchor* rule (plan contract C4): the standalone
    CLI anchors config discovery on the lint *target* rather than the process
    working directory, so ``flakeforge check /path/proj`` honours
    ``/path/proj``'s config even when run from elsewhere.

    :param paths: The positional path arguments as given on the command line;
        relative entries are resolved against *cwd*.
    :param cwd: The directory relative paths and the empty case resolve against.
    :returns: An absolute directory path:

        * no paths -> *cwd*;
        * one path -> that directory, or its parent when the path is a file;
        * several paths -> the deepest common ancestor directory.
    """
    root = Path(cwd).resolve()
    resolved = [_resolve_against(root, path) for path in paths]
    if not resolved:
        return root
    if len(resolved) == 1:
        return _as_directory(resolved[0])
    common = Path(os.path.commonpath([str(path) for path in resolved]))
    return _as_directory(common)


def isolated_config(
    paths: Sequence[Union[str, Path]],
    *,
    cwd: Union[str, Path],
) -> LintConfig:
    """Build a defaults-only configuration for ``--no-config`` isolated mode.

    Skips config-file discovery entirely (plan contracts C3/C6/C7): no
    project-local ``rule_modules`` load, and path patterns supplied on the CLI
    resolve against the discovery anchor (C4) via ``base_dir``. Only built-in
    defaults, the CLI overrides the caller overlays, and installed entry-point
    providers (governed by the merged ``rule_plugins`` flag) take effect.

    :param paths: The positional path arguments; used only to locate the anchor.
    :param cwd: The directory relative paths and the empty case resolve against.
    :returns: An empty :class:`LintConfig` whose ``base_dir`` is the anchor.
    """
    return LintConfig(base_dir=discovery_anchor(paths, cwd=cwd))


def _resolve_against(root: Path, path: Union[str, Path]) -> Path:
    """Return *path* resolved to an absolute location under *root* if relative."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _as_directory(path: Path) -> Path:
    """Return *path* itself, or its parent when it names an existing file."""
    return path.parent if path.is_file() else path


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    *,
    cwd: Optional[Union[str, Path]] = None,
) -> LintConfig:
    """Locate and load the effective lint configuration.

    :param config_path: Explicit config file; when omitted the parent
        directories of *cwd* are searched for ``flakeforge.toml`` or a
        ``pyproject.toml`` carrying a recognised section.
    :param cwd: Directory to start the search from; defaults to the process cwd.
    :returns: The loaded configuration, or an empty one anchored at *cwd*.
    """
    base = (Path(cwd) if cwd is not None else Path.cwd()).resolve()
    if config_path is not None:
        path = Path(config_path)
        if not path.is_absolute():
            path = base / path
        return _load_path(path.resolve())

    for directory in _iter_candidate_directories(base):
        explicit = directory / "flakeforge.toml"
        if explicit.is_file():
            config = _load_path(explicit)
            shadowed = _detect_pyproject_section(directory / "pyproject.toml")
            if shadowed is not None:
                warning = f"pyproject.toml {shadowed} is shadowed by flakeforge.toml; remove one"
                config = config.merge(warnings=config.warnings + (warning,))
            return config

        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            loaded = _load_pyproject(pyproject)
            if loaded is not None:
                return loaded

    return LintConfig(base_dir=base)


def _detect_pyproject_section(pyproject: Path) -> Optional[str]:
    """Report which ``flakeforge`` section a sibling ``pyproject.toml`` defines.

    Used only by the same-directory shadow check in :func:`load_config`: when a
    ``flakeforge.toml`` wins over a ``pyproject.toml`` in the same directory
    (plan contract C3), this names the ``pyproject.toml`` section being shadowed
    so the caller can warn about it. It merely *detects* section presence and
    never validates the shadowed body, so an unknown key or wrong-typed value in
    a section that will not be loaded cannot be turned into an error. A file that
    is missing or cannot be parsed simply yields ``None``.

    :param pyproject: Candidate ``pyproject.toml`` path in the same directory as
        the winning ``flakeforge.toml``.
    :returns: ``"[tool.flakeforge]"`` or the legacy ``"[tool.flake8_lint]"`` when
        that section is present (mirroring the precedence of
        :func:`_load_pyproject`), else ``None``.
    """
    if not pyproject.is_file():
        return None
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        # A sibling we cannot even parse is not a config that would ever be
        # loaded, so no shadow can be attributed to it; the winning
        # flakeforge.toml stands and detection reports no section.
        payload = {}
    tool_section = payload.get("tool")
    if not isinstance(tool_section, dict):
        return None
    if "flakeforge" in tool_section:
        return "[tool.flakeforge]"
    if "flake8_lint" in tool_section:
        return "[tool.flake8_lint]"
    return None


def _load_path(path: Path) -> LintConfig:
    """Load config from an explicit file, dispatching on its filename."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if path.name == "pyproject.toml":
        loaded = _load_pyproject(path, data=data)
        if loaded is None:
            raise ConfigValidationError(f"{path} does not define [tool.flakeforge] or [tool.flake8_lint]")
        return loaded
    if not isinstance(data, dict):
        raise ConfigValidationError(f"{path} must contain a top-level TOML table")
    section, source = _standalone_section(data, path)
    return LintConfig.from_mapping(
        section,
        base_dir=path.parent.resolve(),
        config_path=path.resolve(),
        source=source,
    )


def _standalone_section(data: dict[str, Any], path: Path) -> tuple[dict[str, Any], str]:
    """Resolve a standalone ``flakeforge.toml`` body to its option table.

    Accepts either flat top-level keys or a single ``[tool.flakeforge]`` wrapper
    table, so a snippet can be copied between ``flakeforge.toml`` and
    ``pyproject.toml``. Mixing both forms in one file is rejected.

    :param data: The parsed top-level TOML table.
    :param path: The file the table came from (used only for its display name).
    :returns: A ``(section, source_label)`` pair for :meth:`LintConfig.from_mapping`.
    :raises ConfigValidationError: If the wrapper table is malformed, or if both
        flat keys and the wrapper table are present.
    """
    tool = data.get("tool")
    wrapper: Optional[dict[str, Any]] = None
    if isinstance(tool, dict) and "flakeforge" in tool:
        wrapper = tool["flakeforge"]
        if not isinstance(wrapper, dict):
            raise ConfigValidationError(f"{path.name}: [tool.flakeforge] must be a table")
    if wrapper is None:
        return data, path.name
    if any(key != "tool" for key in data):
        raise ConfigValidationError(
            f"{path.name}: set options either as top-level keys or under [tool.flakeforge], not both"
        )
    return wrapper, f"{path.name} [tool.flakeforge]"


def validate_config(config: LintConfig, known_codes: Sequence[str]) -> LintConfig:
    """Validate *config* selectors against *known_codes* and fold in warnings.

    :param config: Configuration whose ``select``/``ignore`` entries are checked.
    :param known_codes: All rule codes currently registered.
    :returns: A configuration with validated selectors and merged warnings.
    :raises ConfigValidationError: If a selector matches no known rule code
        outside of legacy mode.
    """
    warnings = list(config.warnings)
    normalized_known = tuple(code.upper() for code in known_codes)
    select = _validate_rule_selectors(
        config.select,
        known_codes=normalized_known,
        field_name="select",
        legacy_mode=config.legacy_mode,
        warnings=warnings,
    )
    ignore = _validate_rule_selectors(
        config.ignore,
        known_codes=normalized_known,
        field_name="ignore",
        legacy_mode=config.legacy_mode,
        warnings=warnings,
    )
    return config.merge(select=select, ignore=ignore, warnings=tuple(warnings))


def _load_pyproject(path: Path, *, data: Optional[dict[str, Any]] = None) -> Optional[LintConfig]:
    """Extract a config from a ``pyproject.toml`` tool section, if present."""
    payload = data
    if payload is None:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    tool_section = payload.get("tool")
    if tool_section is None:
        return None
    if not isinstance(tool_section, dict):
        raise ConfigValidationError(f"{path} has invalid [tool] data")

    if "flakeforge" in tool_section:
        section = tool_section["flakeforge"]
        if not isinstance(section, dict):
            raise ConfigValidationError(f"{path} has invalid [tool.flakeforge] data")
        return LintConfig.from_mapping(
            section,
            base_dir=path.parent.resolve(),
            config_path=path.resolve(),
            source=f"{path.name} [tool.flakeforge]",
        )

    if "flake8_lint" in tool_section:
        section = tool_section["flake8_lint"]
        if not isinstance(section, dict):
            raise ConfigValidationError(f"{path} has invalid [tool.flake8_lint] data")
        return LintConfig.from_mapping(
            section,
            base_dir=path.parent.resolve(),
            config_path=path.resolve(),
            legacy_mode=True,
            warnings=(LEGACY_SECTION_WARNING,),
            source=f"{path.name} [tool.flake8_lint]",
        )

    return None


def _iter_candidate_directories(base: Path) -> Iterable[Path]:
    """Yield *base* and each ancestor directory up to the filesystem root."""
    current = base
    while True:
        yield current
        if current.parent == current:
            return
        current = current.parent


def _validate_rule_selectors(
    values: Sequence[str],
    *,
    known_codes: Sequence[str],
    field_name: str,
    legacy_mode: bool,
    warnings: list[str],
) -> tuple[str, ...]:
    """Return the subset of *values* whose codes match a known prefix.

    Unknown selectors raise :class:`ConfigValidationError`, except in legacy
    mode where they are dropped and recorded as a warning instead.
    """
    if not values:
        return ()

    valid: list[str] = []
    unknown: list[str] = []
    for value in values:
        normalized = value.upper()
        if any(code.startswith(normalized) for code in known_codes):
            if normalized not in valid:
                valid.append(normalized)
            continue
        unknown.append(normalized)

    if unknown and legacy_mode:
        warnings.append(
            f"Ignoring unknown legacy {field_name} entr{'y' if len(unknown) == 1 else 'ies'}: " + ", ".join(unknown)
        )
        return tuple(valid)
    if unknown:
        raise ConfigValidationError(f"Unknown {field_name} rule selector(s): " + ", ".join(unknown))
    return tuple(valid)


def _as_str_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    """Coerce a TOML array into a tuple of strings, validating element types."""
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ConfigValidationError(f"{field_name} must be an array of strings")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ConfigValidationError(f"{field_name} entries must be strings")
        items.append(item)
    return tuple(items)


def _as_upper_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    """Coerce a TOML array into a tuple of upper-cased strings."""
    return tuple(item.upper() for item in _as_str_tuple(value, field_name=field_name))


def _as_path_pattern_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    """Coerce a TOML array of relative path patterns, rejecting absolute ones.

    The path-pattern config keys (``include``, ``exclude``, ``noqa_allowed``,
    ``noqa_forbidden``) resolve against the config file's directory
    (``base_dir``, plan contract C6), so an absolute pattern -- a POSIX
    ``/etc`` or a Windows drive/UNC path -- would silently escape that anchor.
    Rejecting it here (one place, both config surfaces, including the lenient
    legacy ``[tool.flake8_lint]`` section, since this is a value error rather
    than an unknown key) also guarantees :func:`api._safe_traversal_root` never
    receives an absolute config pattern. Relative patterns, including ones with
    ``..`` segments (e.g. ``../src``), remain supported.

    :param value: The raw TOML value for *field_name*.
    :param field_name: The config key, used in error messages.
    :returns: The validated tuple of relative path patterns.
    :raises ConfigValidationError: If *value* is not an array of strings, or any
        entry is an absolute path.
    """
    patterns = _as_str_tuple(value, field_name=field_name)
    for pattern in patterns:
        if _is_absolute_pattern(pattern):
            raise ConfigValidationError(
                f"{field_name} pattern {pattern!r} must be relative to the config file directory, not absolute"
            )
    return patterns


def _is_absolute_pattern(pattern: str) -> bool:
    """Return whether *pattern* is anchored outside the config file directory.

    Both flavours are checked so a config authored on either platform is
    rejected regardless of the host running the linter: any Windows anchor
    (drive-rooted ``C:\\...``, drive-relative ``C:foo``, root-relative ``\\foo``,
    UNC ``\\\\host\\share``) and ``/``-rooted POSIX paths all count. ``~`` is a
    literal segment because patterns are never user-expanded.
    """
    return bool(PureWindowsPath(pattern).anchor) or PurePosixPath(pattern).is_absolute()


def _normalize_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    """Upper-case each rule code in *values*."""
    return tuple(value.upper() for value in values)


def _as_bool(value: Any, *, field_name: str) -> bool:
    """Return *value* if it is a real ``bool``, else raise a validation error."""
    if isinstance(value, bool):
        return value
    raise ConfigValidationError(f"{field_name} must be a boolean")


def _as_str(value: Any, *, field_name: str) -> str:
    """Return *value* if it is a ``str``, else raise a validation error."""
    if isinstance(value, str):
        return value
    raise ConfigValidationError(f"{field_name} must be a string")


#: The single source of truth for the config surface (plan contract C5): each
#: key maps to ``(coercer, default)``. :meth:`LintConfig.from_mapping` iterates
#: this mapping, so both ``flakeforge.toml`` and ``[tool.flakeforge]`` accept the
#: same keys, and adding a future setting is a one-line entry here. The keys must
#: match the coerced ``LintConfig`` field names exactly.
_CONFIG_SCHEMA: dict[str, tuple[Callable[..., Any], Any]] = {
    "include": (_as_path_pattern_tuple, ()),
    "exclude": (_as_path_pattern_tuple, ()),
    "select": (_as_upper_tuple, ()),
    "ignore": (_as_upper_tuple, ()),
    "allow_noqa": (_as_bool, True),
    "noqa_allowed": (_as_path_pattern_tuple, ()),
    "noqa_forbidden": (_as_path_pattern_tuple, ()),
    "rule_modules": (_as_str_tuple, ()),
    "rule_plugins": (_as_bool, True),
    "output_format": (_as_str, "text"),
    "statistics": (_as_bool, False),
}
