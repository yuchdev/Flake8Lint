import textwrap
from dataclasses import dataclass

import pytest

from flake8_lint import RuleContext, RuleRegistry, RuleViolation, check_source
from flake8_lint.config import LintConfig
from flake8_lint.registry import (
    DuplicateRuleCodeError,
    InvalidRuleCodeError,
    RuleProviderLoadError,
    resolve_registry,
)


class LocalRule:
    code = "ORG001"
    description = "Local rule"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "local rule")


def test_direct_rule_registration_and_filtering() -> None:
    registry = RuleRegistry()
    registry.register(LocalRule(), provider="tests.local")
    assert [
        violation.code for violation in check_source("x = 1\n", rules=[LocalRule()])
    ] == ["ORG001"]
    assert check_source("x = 1\n", config=LintConfig(ignore=("ORG",)), rules=[LocalRule()]) == ()


def test_project_local_rule_module_registers_rules(tmp_path, monkeypatch) -> None:
    package = tmp_path / "demo_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            from flake8_lint import RuleRegistry, RuleViolation

            class NoPrintRule:
                code = "ORG001"
                description = "Local rule"

                def check(self, context):
                    yield RuleViolation(context.filename, 1, 0, self.code, "local rule")

            def register_rules(registry: RuleRegistry) -> None:
                registry.register(NoPrintRule(), provider="demo_project.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = resolve_registry(
        rule_modules=("demo_project.lint_rules",),
        include_entry_points=False,
    )
    violations = check_source(
        "x = 1\n",
        filename="demo.py",
        config=LintConfig(select=("ORG001",)),
        registry=registry,
    )
    assert [violation.code for violation in violations] == ["ORG001"]


def test_missing_rule_module_reports_module_name(tmp_path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(RuleProviderLoadError, match="missing\\.module"):
        resolve_registry(rule_modules=("missing.module",), include_entry_points=False)


def test_duplicate_rule_codes_fail_clearly(tmp_path, monkeypatch) -> None:
    package = tmp_path / "dup_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            class DuplicateRule:
                code = "X001"
                description = "duplicate"

                def check(self, context):
                    return ()

            def register_rules(registry):
                registry.register(DuplicateRule(), provider="dup_project.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(DuplicateRuleCodeError):
        resolve_registry(rule_modules=("dup_project.lint_rules",), include_entry_points=False)


def test_invalid_rule_code_fails_clearly() -> None:
    class BadRule:
        code = "org1"
        description = "bad"

        def check(self, context):
            return ()

    registry = RuleRegistry()
    with pytest.raises(InvalidRuleCodeError):
        registry.register(BadRule(), provider="tests.bad")


def test_custom_noqa_suppresses_matching_rule() -> None:
    source = "x = 1  # noqa: ORG001\n"
    assert (
        check_source(
            source,
            filename="sample.py",
            config=LintConfig(select=("ORG001",), noqa_allowed=("sample.py",)),
            rules=[LocalRule()],
        )
        == ()
    )


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    value: str
    loader: object
    dist: object | None = None

    def load(self):
        return self.loader


class FakeEntryPoints(list):
    def select(self, *, group: str):
        assert group == "flake8_lint.rules"
        return self


def test_installed_provider_entry_points_are_loaded_deterministically(monkeypatch) -> None:
    def register_second(registry: RuleRegistry) -> None:
        class SecondRule:
            code = "ZZZ001"
            description = "second"

            def check(self, context):
                return ()

        registry.register(SecondRule(), provider="pkg.second")

    def register_first(registry: RuleRegistry) -> None:
        class FirstRule:
            code = "AAA001"
            description = "first"

            def check(self, context):
                return ()

        registry.register(FirstRule(), provider="pkg.first")

    monkeypatch.setattr(
        "flake8_lint.registry.metadata.entry_points",
        lambda: FakeEntryPoints(
            [
                FakeEntryPoint("zzz", "pkg.second:register_rules", register_second),
                FakeEntryPoint("aaa", "pkg.first:register_rules", register_first),
            ]
        ),
    )
    registry = resolve_registry()
    assert registry.known_codes()[:2] == ("AAA001", "X001")
    assert "ZZZ001" in registry.known_codes()


def test_installed_provider_load_error_names_provider(monkeypatch) -> None:
    def boom(registry):
        del registry
        raise RuntimeError("broken provider")

    monkeypatch.setattr(
        "flake8_lint.registry.metadata.entry_points",
        lambda: FakeEntryPoints([FakeEntryPoint("boom", "pkg.boom:register_rules", boom)]),
    )
    with pytest.raises(RuleProviderLoadError, match="boom"):
        resolve_registry()
