"""Rule registry and provider loading."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module, metadata
from typing import Any, Protocol

ENTRY_POINT_GROUP = "flake8_lint.rules"
RegisterRulesCallable = Callable[["RuleRegistry"], None]
RULE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*\d{3}$")


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


class InvalidRuleCodeError(ValueError):
    """Raised when a rule code does not follow the public naming contract."""


class RuleProviderLoadError(RuntimeError):
    """Raised when a rule provider cannot be imported or registered."""


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
        code = str(rule.code)
        validate_rule_code(code)
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
        try:
            _load_register_function(module_name)(registry)
        except (DuplicateRuleCodeError, InvalidRuleCodeError):
            raise
        except Exception as exc:
            raise RuleProviderLoadError(
                f"Failed to load rule module {module_name}: {exc}"
            ) from exc

    if include_entry_points:
        for entry_point in _iter_entry_points():
            provider_label = _describe_entry_point(entry_point)
            try:
                register_rules = entry_point.load()
                register_rules(registry)
            except (DuplicateRuleCodeError, InvalidRuleCodeError):
                raise
            except Exception as exc:
                raise RuleProviderLoadError(
                    f"Failed to load installed rule provider {provider_label}: {exc}"
                ) from exc

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
        selected = entry_points.select(group=ENTRY_POINT_GROUP)
    else:
        selected = entry_points.get(ENTRY_POINT_GROUP, [])
    return tuple(sorted(selected, key=lambda entry_point: (entry_point.name, entry_point.value)))


def validate_rule_code(code: str) -> str:
    if not RULE_CODE_RE.fullmatch(code):
        raise InvalidRuleCodeError(
            f"Invalid rule code {code!r}: expected an uppercase alphanumeric prefix "
            "followed by three digits"
        )
    return code


def _describe_entry_point(entry_point) -> str:
    dist_name = getattr(getattr(entry_point, "dist", None), "name", None)
    if dist_name:
        return f"{entry_point.name} ({dist_name}: {entry_point.value})"
    return f"{entry_point.name} ({entry_point.value})"
