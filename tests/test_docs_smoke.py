import ast

from flake8_lint import RuleContext, RuleViolation, check_source, lint_paths
from flake8_lint.config import LintConfig


class NoPrintRule:
    code = "ACME001"
    description = "Do not call print() in production code."

    def check(self, context: RuleContext):
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


def test_custom_rule_docs_example_unit_flow() -> None:
    violations = check_source(
        'print("hello")\n',
        filename="example.py",
        config=LintConfig(select=("ACME001",)),
        rules=[NoPrintRule()],
    )
    assert [violation.code for violation in violations] == ["ACME001"]


def test_custom_rule_docs_example_lint_paths_flow(tmp_path) -> None:
    package = tmp_path / "my_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        "import ast\n"
        "from flake8_lint import RuleContext, RuleRegistry, RuleViolation\n\n"
        "class NoPrintRule:\n"
        '    code = "ACME001"\n'
        '    description = "Do not call print() in production code."\n\n'
        "    def check(self, context: RuleContext):\n"
        "        for node in ast.walk(context.tree):\n"
        "            if (\n"
        "                isinstance(node, ast.Call)\n"
        "                and isinstance(node.func, ast.Name)\n"
        "                and node.func.id == \"print\"\n"
        "            ):\n"
        "                yield RuleViolation(\n"
        "                    context.filename,\n"
        "                    node.lineno,\n"
        "                    node.col_offset,\n"
        "                    self.code,\n"
        "                    self.description,\n"
        "                )\n\n"
        "def register_rules(registry: RuleRegistry) -> None:\n"
        '    registry.register(NoPrintRule(), provider="my_project.lint_rules")\n',
        encoding="utf-8",
    )
    sample = tmp_path / "src"
    sample.mkdir()
    (sample / "example.py").write_text('print("hello")\n', encoding="utf-8")

    import sys

    sys.path.insert(0, str(tmp_path))
    try:
        result = lint_paths(
            [sample],
            config=LintConfig(select=("ACME001",), rule_modules=("my_project.lint_rules",)),
        )
    finally:
        sys.path.remove(str(tmp_path))

    assert [violation.code for violation in result.violations] == ["ACME001"]
