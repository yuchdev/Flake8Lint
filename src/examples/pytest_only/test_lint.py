from pathlib import Path

from flake8_lint.config import load_config
from flake8_lint.testing import assert_lint_clean


def test_lint() -> None:
    config = load_config(cwd=Path(__file__).parent)
    assert_lint_clean(Path(__file__).parent / "app.py", config=config)
