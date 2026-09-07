import ast

from flake8_lint.api import RuleContext, RuleViolation, check_tree
from flake8_lint.config import LintConfig
from flake8_lint.registry import RuleRegistry

SOURCE = "\n".join(
    [
        "def handler() -> int:",
        '    """Handle a broad exception."""',
        "    try:",
        "        risky()",
        "    except Exception:  # noqa: X002",
        "        return 1",
    ]
)


def test_noqa_allowed_suppresses_matching_rule() -> None:
    tree = ast.parse(SOURCE, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        SOURCE,
        config=LintConfig(select=("X002",), noqa_allowed=("X002",)),
    )
    assert violations == ()


def test_noqa_forbidden_blocks_matching_rule() -> None:
    tree = ast.parse(SOURCE, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        SOURCE,
        config=LintConfig(select=("X002",), noqa_forbidden=("X002",)),
    )
    assert [violation.code for violation in violations] == ["X002"]


def test_allow_noqa_false_disables_noqa_suppression() -> None:
    tree = ast.parse(SOURCE, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        SOURCE,
        config=LintConfig(select=("X002",), allow_noqa=False),
    )
    assert [violation.code for violation in violations] == ["X002"]


class InlineRule:
    code = "ORG001"
    description = "inline"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "inline violation")


def test_noqa_parsing_ignores_hash_inside_string_literals() -> None:
    registry = RuleRegistry()
    registry.register(InlineRule(), provider="tests.inline")
    source = 'value = "# not a comment"  # noqa: ORG001\n'
    tree = ast.parse(source, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        source,
        config=LintConfig(select=("ORG001",), noqa_allowed=("ORG001",)),
        registry=registry,
    )
    assert violations == ()


def test_noqa_prefix_suppression_matches_rule_families() -> None:
    tree = ast.parse(SOURCE.replace("# noqa: X002", "# noqa: X0"), filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        SOURCE.replace("# noqa: X002", "# noqa: X0"),
        config=LintConfig(select=("X002",), noqa_allowed=("X0",)),
    )
    assert violations == ()
