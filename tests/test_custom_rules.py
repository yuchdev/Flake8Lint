import ast
import textwrap

import pytest

from flake8_lint.api import check_tree
from flake8_lint.config import LintConfig
from flake8_lint.registry import DuplicateRuleCodeError, resolve_registry


def test_project_local_rule_module_registers_rules(tmp_path, monkeypatch) -> None:
    package = tmp_path / "demo_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            from flake8_lint.api import RuleViolation

            class LocalRule:
                code = "ORG001"
                description = "Local rule"

                def check(self, context):
                    yield RuleViolation(context.filename, 1, 0, self.code, "local rule")

            def register_rules(registry):
                registry.register(LocalRule(), provider="demo_project.lint_rules")
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
    tree = ast.parse("x = 1", filename="demo.py")
    violations = check_tree(
        tree,
        "demo.py",
        "x = 1\n",
        config=LintConfig(select=("ORG001",)),
        registry=registry,
    )
    assert [violation.code for violation in violations] == ["ORG001"]


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
