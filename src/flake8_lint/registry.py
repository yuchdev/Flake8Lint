"""Rule registry and provider loading."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module, metadata
from typing import Any, Protocol

ENTRY_POINT_GROUP = "flake8_lint.rules"
RegisterRulesCallable = Callable[["RuleRegistry"], None]


class RuleLike(Protocol):
    code: str
    description: str

    def check(self, context: Any):
        ...


@dataclass(frozen=True)
class RuleRegistration:
    code: str
    description: str
    rule: RuleLike
    provider: str
    enabled: bool = True
    reserved: bool = False


class DuplicateRuleCodeError(ValueError):
    """Raised when multiple rules claim the same rule code."""


class RuleRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, RuleRegistration] = {}

    def register(
        self,
        rule: RuleLike,
        *,
        provider: str,
        enabled: bool = True,
        reserved: bool = False,
    ) -> None:
        code = rule.code.upper()
        if code in self._registrations:
            existing = self._registrations[code]
            raise DuplicateRuleCodeError(
                f"Duplicate rule code {code}: {existing.provider} and {provider}"
            )
        self._registrations[code] = RuleRegistration(
            code=code,
            description=rule.description,
            rule=rule,
            provider=provider,
            enabled=enabled,
            reserved=reserved,
        )

    def get(self, code: str) -> RuleRegistration:
        return self._registrations[code.upper()]

    def all(self) -> tuple[RuleRegistration, ...]:
        return tuple(self._registrations[code] for code in sorted(self._registrations))

    def enabled_rules(self) -> tuple[RuleRegistration, ...]:
        return tuple(registration for registration in self.all() if registration.enabled)

    def known_codes(self) -> tuple[str, ...]:
        return tuple(registration.code for registration in self.all())


def resolve_registry(
    *,
    rule_modules: Iterable[str] = (),
    include_entry_points: bool = True,
) -> RuleRegistry:
    from .rules import builtin_registrations

    registry = RuleRegistry()
    for registration in builtin_registrations():
        registry.register(
            registration.rule,
            provider=registration.provider,
            enabled=registration.enabled,
            reserved=registration.reserved,
        )

    for module_name in rule_modules:
        _load_register_function(module_name)(registry)

    if include_entry_points:
        for entry_point in _iter_entry_points():
            register_rules = entry_point.load()
            register_rules(registry)

    return registry


def _load_register_function(module_name: str) -> RegisterRulesCallable:
    module = import_module(module_name)
    register_rules = getattr(module, "register_rules", None)
    if register_rules is None or not callable(register_rules):
        raise AttributeError(f"{module_name} does not define callable register_rules(registry)")
    return register_rules


def _iter_entry_points():
    entry_points = metadata.entry_points()
    if hasattr(entry_points, "select"):
        return entry_points.select(group=ENTRY_POINT_GROUP)
    return entry_points.get(ENTRY_POINT_GROUP, [])
