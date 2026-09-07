import pytest

from flake8_lint.testing import assert_lint_clean


def test_assert_lint_clean_passes_for_clean_file(tmp_path) -> None:
    sample = tmp_path / "clean.py"
    sample.write_text(
        'def documented() -> int:\n    """Return a number."""\n    return 1\n',
        encoding="utf-8",
    )
    assert_lint_clean(sample)


def test_assert_lint_clean_raises_for_violation(tmp_path) -> None:
    sample = tmp_path / "bad.py"
    sample.write_text("def f():\n    return 1\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="X005"):
        assert_lint_clean(sample)
