import ast

from flake8_lint.api import LintResult, RuleContext, RuleViolation, check_tree
from flake8_lint.config import LintConfig
from flake8_lint.registry import RuleRegistry


class DemoRule:
    code = "ORG001"
    description = "demo"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "demo violation")


def test_lint_result_ok_property() -> None:
    result = LintResult(violations=(), files_checked=1)
    assert result.ok is True


def test_check_tree_applies_select_and_ignore_to_custom_rules() -> None:
    registry = RuleRegistry()
    registry.register(DemoRule(), provider="tests.demo")
    tree = ast.parse("x = 1", filename="sample.py")
    config = LintConfig(select=("ORG001",), ignore=("ORG999",))
    violations = check_tree(tree, "sample.py", "x = 1\n", config=config, registry=registry)
    assert [violation.code for violation in violations] == ["ORG001"]
