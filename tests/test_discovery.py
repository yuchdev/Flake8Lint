from flake8_lint.config import LintConfig
from flake8_lint.discovery import discover_python_files


def test_discovery_skips_default_excluded_directories(tmp_path) -> None:
    included = tmp_path / "src"
    included.mkdir()
    (included / "module.py").write_text("x = 1\n", encoding="utf-8")
    cache = tmp_path / ".pytest_cache"
    cache.mkdir()
    (cache / "cached.py").write_text("x = 2\n", encoding="utf-8")
    files = discover_python_files((tmp_path,), config=LintConfig())
    assert files == ((included / "module.py").resolve(),)


def test_discovery_applies_include_and_deduplicates(tmp_path) -> None:
    included = tmp_path / "pkg"
    included.mkdir()
    file_path = included / "target.py"
    file_path.write_text("x = 1\n", encoding="utf-8")
    files = discover_python_files((tmp_path, included), config=LintConfig(include=("*/target.py",)))
    assert files == (file_path.resolve(),)
