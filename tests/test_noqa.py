import ast
from pathlib import Path

from flake8_lint import RuleContext, RuleRegistry, RuleViolation, check_tree
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


class InlineRule:
    code = "ORG001"
    description = "inline"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "inline violation")


def test_bare_noqa_suppresses_matching_line() -> None:
    source = SOURCE.replace("# noqa: X002", "# noqa")
    violations = check_tree(
        ast.parse(source, filename="sample.py"),
        "sample.py",
        source,
        config=LintConfig(select=("X002",)),
    )
    assert violations == ()


def test_matching_code_noqa_suppresses_only_matching_rule() -> None:
    violations = check_tree(
        ast.parse(SOURCE, filename="sample.py"),
        "sample.py",
        SOURCE,
        config=LintConfig(select=("X002",)),
    )
    assert violations == ()


def test_multiple_codes_noqa_suppresses_matching_rule() -> None:
    source = SOURCE.replace("# noqa: X002", "# noqa: X001, X002")
    violations = check_tree(
        ast.parse(source, filename="sample.py"),
        "sample.py",
        source,
        config=LintConfig(select=("X002",)),
    )
    assert violations == ()


def test_nonmatching_noqa_does_not_suppress() -> None:
    source = SOURCE.replace("# noqa: X002", "# noqa: X001")
    violations = check_tree(
        ast.parse(source, filename="sample.py"),
        "sample.py",
        source,
        config=LintConfig(select=("X002",)),
    )
    assert [violation.code for violation in violations] == ["X002"]


def test_allow_noqa_false_disables_noqa_suppression() -> None:
    violations = check_tree(
        ast.parse(SOURCE, filename="sample.py"),
        "sample.py",
        SOURCE,
        config=LintConfig(select=("X002",), allow_noqa=False),
    )
    assert [violation.code for violation in violations] == ["X002"]


def test_source_absent_disables_noqa_suppression() -> None:
    violations = check_tree(
        ast.parse(SOURCE, filename="sample.py"),
        "sample.py",
        None,
        config=LintConfig(select=("X002",)),
    )
    assert [violation.code for violation in violations] == ["X002"]


def test_noqa_allowed_path_allows_only_matching_files(tmp_path) -> None:
    filename = str(tmp_path / "src" / "sample.py")
    violations = check_tree(
        ast.parse(SOURCE, filename=filename),
        filename,
        SOURCE,
        config=LintConfig(
            select=("X002",),
            noqa_allowed=("src/sample.py",),
            base_dir=tmp_path,
        ),
    )
    assert violations == ()


def test_noqa_forbidden_path_wins_over_noqa_allowed(tmp_path) -> None:
    filename = str(tmp_path / "src" / "sample.py")
    violations = check_tree(
        ast.parse(SOURCE, filename=filename),
        filename,
        SOURCE,
        config=LintConfig(
            select=("X002",),
            noqa_allowed=("src",),
            noqa_forbidden=("src/sample.py",),
            base_dir=tmp_path,
        ),
    )
    assert [violation.code for violation in violations] == ["X002"]


def test_noqa_parsing_ignores_hash_inside_string_literals() -> None:
    registry = RuleRegistry()
    registry.register(InlineRule(), provider="tests.inline")
    source = 'value = "# not a comment"  # noqa: ORG001\n'
    tree = ast.parse(source, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        source,
        config=LintConfig(select=("ORG001",), noqa_allowed=("sample.py",)),
        registry=registry,
    )
    assert violations == ()


def test_custom_rule_code_is_suppressed_by_matching_noqa() -> None:
    registry = RuleRegistry()
    registry.register(InlineRule(), provider="tests.inline")
    source = "x = 1  # noqa: ORG001\n"
    tree = ast.parse(source, filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        source,
        config=LintConfig(select=("ORG",), noqa_allowed=("sample.py",)),
        registry=registry,
    )
    assert violations == ()
