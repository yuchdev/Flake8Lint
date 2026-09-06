"""Typed configuration loading for flake8-lint."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LintConfig:
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    select: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    allow_noqa: bool = True
    noqa_allowed: tuple[str, ...] = ()
    noqa_forbidden: tuple[str, ...] = ()
    rule_modules: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "LintConfig":
        payload = data or {}
        return cls(
            include=_as_str_tuple(payload.get("include")),
            exclude=_as_str_tuple(payload.get("exclude")),
            select=_as_upper_tuple(payload.get("select")),
            ignore=_as_upper_tuple(payload.get("ignore")),
            allow_noqa=bool(payload.get("allow_noqa", True)),
            noqa_allowed=_as_upper_tuple(payload.get("noqa_allowed")),
            noqa_forbidden=_as_upper_tuple(payload.get("noqa_forbidden")),
            rule_modules=_as_str_tuple(payload.get("rule_modules")),
        )

    def merge(
        self,
        *,
        include: tuple[str, ...] | None = None,
        exclude: tuple[str, ...] | None = None,
        select: tuple[str, ...] | None = None,
        ignore: tuple[str, ...] | None = None,
        allow_noqa: bool | None = None,
        noqa_allowed: tuple[str, ...] | None = None,
        noqa_forbidden: tuple[str, ...] | None = None,
        rule_modules: tuple[str, ...] | None = None,
    ) -> "LintConfig":
        return replace(
            self,
            include=self.include if include is None else include,
            exclude=self.exclude if exclude is None else exclude,
            select=self.select if select is None else select,
            ignore=self.ignore if ignore is None else ignore,
            allow_noqa=self.allow_noqa if allow_noqa is None else allow_noqa,
            noqa_allowed=self.noqa_allowed if noqa_allowed is None else noqa_allowed,
            noqa_forbidden=self.noqa_forbidden if noqa_forbidden is None else noqa_forbidden,
            rule_modules=self.rule_modules if rule_modules is None else rule_modules,
        )


def load_config(
    config_path: str | Path | None = None,
    *,
    cwd: str | Path | None = None,
) -> LintConfig:
    base = Path(cwd) if cwd is not None else Path.cwd()
    if config_path is not None:
        path = Path(config_path)
        if not path.is_absolute():
            path = base / path
        return _load_path(path)

    explicit = base / "flake8_lint.toml"
    if explicit.is_file():
        return _load_path(explicit)

    pyproject = base / "pyproject.toml"
    if pyproject.is_file():
        return _load_path(pyproject)

    return LintConfig()


def _load_path(path: Path) -> LintConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if path.name == "pyproject.toml":
        tool_section = data.get("tool", {})
        section = tool_section.get("flake8_lint") or tool_section.get("flake8_lint_tests") or {}
        if not isinstance(section, dict):
            section = {}
        return LintConfig.from_mapping(section)
    return LintConfig.from_mapping(data if isinstance(data, dict) else {})


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _as_upper_tuple(value: Any) -> tuple[str, ...]:
    return tuple(item.upper() for item in _as_str_tuple(value))
