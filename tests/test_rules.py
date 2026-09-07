from pathlib import Path

import pytest

from flake8_lint import check_file, check_source
from flake8_lint.config import LintConfig
from flake8_lint.registry import resolve_registry


@pytest.mark.parametrize(
    ("code", "source"),
    [
        ("X001", "def f():\n    try:\n        run()\n    except:\n        return 1\n"),
        (
            "X002",
            "def f():\n"
            '    """Handle a broad exception."""\n'
            "    try:\n"
            "        run()\n"
            "    except Exception:\n"
            "        raise\n",
        ),
        ("X004", "def f():\n    try:\n        run()\n    except RuntimeError:\n        pass\n"),
        ("X005", "def f():\n    return 1\n"),
        ("X006", "def f():\n    import math\n    return math.ceil(1.2)\n"),
        ("X007", 'def f():\n    """Return a value."""\n    return 1\n'),
        ("X008", "def f() -> None:\n    pass\n"),
        ("X009", 'value = "%s" % name\n'),
        (
            "X010",
            "try:\n"
            "    import missing\n"
            "except ImportError:\n"
            "    fallback = True\n",
        ),
        ("X011", "value: int | None = None\n"),
        ("X012", "value: int | str = 1\n"),
    ],
)
def test_each_builtin_rule_fires_on_a_direct_sample(code: str, source: str) -> None:
    violations = check_source(source, filename="sample.py", config=LintConfig(select=(code,)))
    assert [violation.code for violation in violations] == [code]


def test_registry_includes_reserved_x003() -> None:
    registry = resolve_registry(include_entry_points=False)
    registration = registry.get("X003")
    assert registration.reserved is True
    assert registration.enabled is False


def test_clean_sample_is_clean_for_all_builtin_rules() -> None:
    sample = Path(__file__).parent / "samples" / "clean.py"
    assert check_file(sample) == ()


def test_x003_remains_inactive_even_when_selected() -> None:
    assert check_source("x = 1\n", filename="sample.py", config=LintConfig(select=("X003",))) == ()


def test_x007_ignores_returns_inside_nested_classes(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def outer():\n"
        '    """Outer wrapper."""\n'
        "    class Inner:\n"
        '        """Inner class."""\n'
        "        def method(self) -> int:\n"
        '            """Return a value."""\n'
        "            return 1\n",
        encoding="utf-8",
    )
    violations = check_file(sample, config=LintConfig(select=("X007",)))
    assert violations == ()


def test_union_rules_only_match_top_level_pep604_annotations(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "data: list[int | None] = []\n"
        "mapping: dict[str, int | float] = {}\n",
        encoding="utf-8",
    )
    violations = check_file(sample, config=LintConfig(select=("X011", "X012")))
    assert violations == ()


def test_x012_direct_samples_cover_violation_and_clean_case() -> None:
    base = Path(__file__).parent / "samples"
    violating = check_file(base / "x012_violation.py", config=LintConfig(select=("X012",)))
    clean = check_file(base / "x012_clean.py", config=LintConfig(select=("X012",)))
    assert [violation.code for violation in violating] == ["X012"]
    assert clean == ()


def test_x011_and_x012_do_not_double_report_same_annotation() -> None:
    violations = check_source(
        "value: int | None = None\n",
        filename="sample.py",
        config=LintConfig(select=("X011", "X012")),
    )
    assert [violation.code for violation in violations] == ["X011"]


def test_x005_reports_missing_structured_test_docstring_for_test_functions() -> None:
    source = "def test_case():\n    return 1\n"
    violations = check_source(
        source,
        filename="test_sample.py",
        config=LintConfig(select=("X005",)),
    )
    assert [violation.code for violation in violations] == ["X005"]


def test_x005_reports_incomplete_structured_test_docstring() -> None:
    source = (
        'def test_case():\n'
        '    """[Unit] demo\\n\\nScenario: test\\n"""\n'
        "    return 1\n"
    )
    violations = check_source(
        source,
        filename="tests/test_sample.py",
        config=LintConfig(select=("X005",)),
    )
    assert [violation.code for violation in violations] == ["X005"]


def test_x005_accepts_structured_test_docstring() -> None:
    source = (
        'def test_case():\n'
        '    """[Unit] demo\\n\\nScenario: test\\nBoundaries: none\\n'
        '    On failure, first check: inputs\\n"""\n'
        "    return None\n"
    )
    violations = check_source(
        source,
        filename="tests/test_sample.py",
        config=LintConfig(select=("X005",)),
    )
    assert violations == ()
