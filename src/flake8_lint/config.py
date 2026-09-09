"""Typed configuration loading for flake8-lint."""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional, Union

LEGACY_SECTION_WARNING = "[tool.flake8_lint_tests] is deprecated; rename it to [tool.flake8_lint]."


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
    :ivar noqa_allowed: Path patterns where ``# noqa`` is permitted.
    :ivar noqa_forbidden: Path patterns where ``# noqa`` is rejected.
    :ivar rule_modules: Importable modules contributing extra rules.
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
    ) -> "LintConfig":
        """Build a :class:`LintConfig` from a parsed TOML mapping.

        :param data: Raw config table, or ``None`` for an empty configuration.
        :param base_dir: Directory patterns are resolved against.
        :param config_path: Path the config originated from.
        :param legacy_mode: Whether the data came from a deprecated section.
        :param warnings: Pre-existing warnings to carry forward.
        :returns: A validated, immutable configuration instance.
        """
        payload = data or {}
        return cls(
            include=_as_str_tuple(payload.get("include"), field_name="include"),
            exclude=_as_str_tuple(payload.get("exclude"), field_name="exclude"),
            select=_as_upper_tuple(payload.get("select"), field_name="select"),
            ignore=_as_upper_tuple(payload.get("ignore"), field_name="ignore"),
            allow_noqa=_as_bool(payload.get("allow_noqa", True), field_name="allow_noqa"),
            noqa_allowed=_as_str_tuple(payload.get("noqa_allowed"), field_name="noqa_allowed"),
            noqa_forbidden=_as_str_tuple(
                payload.get("noqa_forbidden"),
                field_name="noqa_forbidden",
            ),
            rule_modules=_as_str_tuple(payload.get("rule_modules"), field_name="rule_modules"),
            base_dir=base_dir,
            config_path=config_path,
            legacy_mode=legacy_mode,
            warnings=tuple(warnings),
        )

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
        warnings: Optional[tuple[str, ...]] = None,
    ) -> "LintConfig":
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
            warnings=self.warnings if warnings is None else warnings,
        )


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    *,
    cwd: Optional[Union[str, Path]] = None,
) -> LintConfig:
    """Locate and load the effective lint configuration.

    :param config_path: Explicit config file; when omitted the parent
        directories of *cwd* are searched for ``flake8_lint.toml`` or a
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
        explicit = directory / "flake8_lint.toml"
        if explicit.is_file():
            return _load_path(explicit)

        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            loaded = _load_pyproject(pyproject)
            if loaded is not None:
                return loaded

    return LintConfig(base_dir=base)


def _load_path(path: Path) -> LintConfig:
    """Load config from an explicit file, dispatching on its filename."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if path.name == "pyproject.toml":
        loaded = _load_pyproject(path, data=data)
        if loaded is None:
            raise ConfigValidationError(
                f"{path} does not define [tool.flake8_lint] or [tool.flake8_lint_tests]"
            )
        return loaded
    if not isinstance(data, dict):
        raise ConfigValidationError(f"{path} must contain a top-level TOML table")
    return LintConfig.from_mapping(
        data,
        base_dir=path.parent.resolve(),
        config_path=path.resolve(),
    )


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

    if "flake8_lint" in tool_section:
        section = tool_section["flake8_lint"]
        if not isinstance(section, dict):
            raise ConfigValidationError(f"{path} has invalid [tool.flake8_lint] data")
        return LintConfig.from_mapping(
            section,
            base_dir=path.parent.resolve(),
            config_path=path.resolve(),
        )

    if "flake8_lint_tests" in tool_section:
        section = tool_section["flake8_lint_tests"]
        if not isinstance(section, dict):
            raise ConfigValidationError(f"{path} has invalid [tool.flake8_lint_tests] data")
        return LintConfig.from_mapping(
            section,
            base_dir=path.parent.resolve(),
            config_path=path.resolve(),
            legacy_mode=True,
            warnings=(LEGACY_SECTION_WARNING,),
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
            f"Ignoring unknown legacy {field_name} entr{'y' if len(unknown) == 1 else 'ies'}: "
            + ", ".join(unknown)
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


def _normalize_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    """Upper-case each rule code in *values*."""
    return tuple(value.upper() for value in values)


def _as_bool(value: Any, *, field_name: str) -> bool:
    """Return *value* if it is a real ``bool``, else raise a validation error."""
    if isinstance(value, bool):
        return value
    raise ConfigValidationError(f"{field_name} must be a boolean")
