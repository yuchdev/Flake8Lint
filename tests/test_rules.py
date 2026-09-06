from pathlib import Path

from flake8_lint.api import check_file
from flake8_lint.config import LintConfig
from flake8_lint.registry import resolve_registry


def test_registry_includes_reserved_x003() -> None:
    registry = resolve_registry(include_entry_points=False)
    registration = registry.get("X003")
    assert registration.reserved is True
    assert registration.enabled is False


def test_builtin_rules_detect_known_samples() -> None:
    sample = Path(__file__).parent / "samples" / "broad_exception.py"
    violations = check_file(sample, config=LintConfig(select=("X002",)))
    assert [violation.code for violation in violations] == ["X002"]


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


def test_x006_flags_imports_inside_class_bodies(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "class Demo:\n"
        '    """Demo class."""\n'
        "    import math\n",
        encoding="utf-8",
    )
    violations = check_file(sample, config=LintConfig(select=("X006",)))
    assert [violation.code for violation in violations] == ["X006"]


def test_x008_skips_stub_functions(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def placeholder() -> None:\n"
        "    ...\n",
        encoding="utf-8",
    )
    violations = check_file(sample, config=LintConfig(select=("X008",)))
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
