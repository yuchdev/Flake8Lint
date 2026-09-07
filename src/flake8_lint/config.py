"""Typed configuration loading for flake8-lint."""

from __future__ import annotations

import tomllib
from collections.abc import Sequence
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
            allow_noqa=_as_bool(payload.get("allow_noqa", True), field_name="allow_noqa"),
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
            select=self.select if select is None else _normalize_codes(select),
            ignore=self.ignore if ignore is None else _normalize_codes(ignore),
            allow_noqa=self.allow_noqa if allow_noqa is None else allow_noqa,
            noqa_allowed=(
                self.noqa_allowed if noqa_allowed is None else _normalize_codes(noqa_allowed)
            ),
            noqa_forbidden=(
                self.noqa_forbidden
                if noqa_forbidden is None
                else _normalize_codes(noqa_forbidden)
            ),
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
    if not isinstance(value, Sequence):
        raise TypeError(f"Expected a string or sequence of strings, got {type(value).__name__}")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(
                f"Expected every list item to be a string, got {type(item).__name__}"
            )
        items.append(item)
    return tuple(items)


def _as_upper_tuple(value: Any) -> tuple[str, ...]:
    return tuple(item.upper() for item in _as_str_tuple(value))


def _normalize_codes(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.upper() for value in values)


def _as_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a boolean, got {type(value).__name__}")
