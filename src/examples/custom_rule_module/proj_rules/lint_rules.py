"""Project-local rule module demonstrating the USERNNN extension convention."""

import ast
from collections.abc import Iterable

from flake8_lint import RuleContext, RuleRegistry, RuleViolation


class NoPrintRule:
    """Flag calls to the built-in ``print`` in production code."""

    code = "USER001"
    description = "Do not call print() in production code."

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        """Yield a USER001 violation for every ``print(...)`` call."""
        for node in ast.walk(context.tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                yield RuleViolation(
                    context.filename,
                    node.lineno,
                    node.col_offset,
                    self.code,
                    self.description,
                )


def register_rules(registry: RuleRegistry) -> None:
    """Register the project-local rules with the shared registry."""
    registry.register(NoPrintRule(), provider="proj_rules.lint_rules")
