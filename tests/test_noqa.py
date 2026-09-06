import ast

from flake8_lint.api import check_tree
from flake8_lint.config import LintConfig

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
