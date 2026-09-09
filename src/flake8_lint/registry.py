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
    """Structural type for a rule usable by the registry.

    :ivar code: The rule's unique code (e.g. ``"X001"``).
    :ivar description: Human-readable summary of what the rule enforces.
    """

    code: str
    description: str

    def check(self, context: Any):
        """Yield the rule's violations for the analysis *context*."""
        ...


@dataclass(frozen=True)
class RuleRegistration:
    """A rule bound to its owning provider and enablement metadata.

    :ivar code: The rule's unique code.
    :ivar description: Human-readable rule summary.
    :ivar rule: The callable rule implementation.
    :ivar provider: Identifier of the provider that registered the rule.
    :ivar enabled: Whether the rule runs by default.
    :ivar reserved: Whether the code is reserved and not user-selectable.
    """

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
    """In-memory catalogue mapping rule codes to their registrations."""

    def __init__(self):
        """Initialise an empty registry."""
        self._registrations: dict[str, RuleRegistration] = {}

    def register(
        self,
        rule: RuleLike,
        *,
        provider: str,
        enabled: bool = True,
        reserved: bool = False,
    ):
        """Register *rule* under its code.

        :param rule: The rule to register.
        :param provider: Identifier of the registering provider.
        :param enabled: Whether the rule runs by default.
        :param reserved: Whether the code is reserved and not user-selectable.
        :raises InvalidRuleCodeError: If the rule code is malformed.
        :raises DuplicateRuleCodeError: If the code is already registered.
        """
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
        """Return the registration for *code* (case-insensitive)."""
        return self._registrations[code.upper()]

    def all(self) -> tuple[RuleRegistration, ...]:
        """Return every registration ordered by rule code."""
        return tuple(self._registrations[code] for code in sorted(self._registrations))

    def enabled_rules(self) -> tuple[RuleRegistration, ...]:
        """Return the registrations whose rules are enabled."""
        return tuple(registration for registration in self.all() if registration.enabled)

    def known_codes(self) -> tuple[str, ...]:
        """Return the codes of all registered rules, ordered."""
        return tuple(registration.code for registration in self.all())


def resolve_registry(
    *,
    rule_modules: Iterable[str] = (),
    include_entry_points: bool = True,
) -> RuleRegistry:
    """Build a registry from built-in rules plus any configured providers.

    :param rule_modules: Importable modules exposing ``register_rules``.
    :param include_entry_points: Whether to load installed entry-point providers.
    :returns: A populated :class:`RuleRegistry`.
    :raises RuleProviderLoadError: If a provider fails to import or register.
    :raises DuplicateRuleCodeError: If two providers claim the same code.
    :raises InvalidRuleCodeError: If a provider registers a malformed code.
    """
    # Imported lazily to avoid an import cycle: ``rules`` imports from both
    # ``api`` and this module at import time, so hoisting this to module scope
    # raises ImportError on a partially-initialised module.
    from .rules import builtin_registrations  # noqa: X006

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
        except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
            raise RuleProviderLoadError(f"Failed to load rule module {module_name}: {exc}") from exc

    if include_entry_points:
        for entry_point in _iter_entry_points():
            provider_label = _describe_entry_point(entry_point)
            try:
                register_rules = entry_point.load()
                register_rules(registry)
            except (DuplicateRuleCodeError, InvalidRuleCodeError):
                raise
            except (ImportError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
                raise RuleProviderLoadError(
                    f"Failed to load installed rule provider {provider_label}: {exc}"
                ) from exc

    return registry


def _load_register_function(module_name: str) -> RegisterRulesCallable:
    """Import *module_name* and return its ``register_rules`` callable.

    :raises AttributeError: If the module lacks a callable ``register_rules``.
    """
    module = import_module(module_name)
    register_rules = getattr(module, "register_rules", None)
    if register_rules is None or not callable(register_rules):
        raise AttributeError(f"{module_name} does not define callable register_rules(registry)")
    return register_rules


def _iter_entry_points() -> tuple[metadata.EntryPoint, ...]:
    """Return this project's rule entry points sorted deterministically."""
    entry_points = metadata.entry_points()
    if hasattr(entry_points, "select"):
        selected = entry_points.select(group=ENTRY_POINT_GROUP)
    else:
        selected = entry_points.get(ENTRY_POINT_GROUP, [])
    return tuple(sorted(selected, key=lambda entry_point: (entry_point.name, entry_point.value)))


def validate_rule_code(code: str) -> str:
    """Return *code* unchanged if it matches the rule-code contract.

    :raises InvalidRuleCodeError: If *code* is not an uppercase alphanumeric
        prefix followed by three digits.
    """
    if not RULE_CODE_RE.fullmatch(code):
        raise InvalidRuleCodeError(
            f"Invalid rule code {code!r}: expected an uppercase alphanumeric prefix "
            "followed by three digits"
        )
    return code


def _describe_entry_point(entry_point) -> str:
    """Return a human-readable label for *entry_point*, including its dist."""
    dist_name = getattr(getattr(entry_point, "dist", None), "name", None)
    if dist_name:
        return f"{entry_point.name} ({dist_name}: {entry_point.value})"
    return f"{entry_point.name} ({entry_point.value})"
