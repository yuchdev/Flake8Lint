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
