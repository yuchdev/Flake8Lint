from flake8_lint.config import LintConfig
from flake8_lint.discovery import discover_python_files


def test_discovery_skips_default_excluded_directories(tmp_path) -> None:
    included = tmp_path / "src"
    included.mkdir()
    (included / "module.py").write_text("x = 1\n", encoding="utf-8")
    cache = tmp_path / ".pytest_cache"
    cache.mkdir()
    (cache / "cached.py").write_text("x = 2\n", encoding="utf-8")
    eggs = tmp_path / ".eggs"
    eggs.mkdir()
    (eggs / "egg.py").write_text("x = 3\n", encoding="utf-8")

    files = discover_python_files((tmp_path,), config=LintConfig(base_dir=tmp_path))
    assert files == ((included / "module.py").resolve(),)


def test_discovery_applies_include_and_deduplicates(tmp_path) -> None:
    included = tmp_path / "pkg"
    included.mkdir()
    file_path = included / "target.py"
    file_path.write_text("x = 1\n", encoding="utf-8")

    files = discover_python_files(
        (tmp_path, included),
        config=LintConfig(include=("pkg/target.py",), base_dir=tmp_path),
    )
    assert files == (file_path.resolve(),)


def test_discovery_exclude_directory_recursively_wins(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    excluded = src / "generated"
    excluded.mkdir()
    keep = src / "keep.py"
    drop = excluded / "drop.py"
    keep.write_text("x = 1\n", encoding="utf-8")
    drop.write_text("x = 2\n", encoding="utf-8")

    files = discover_python_files(
        (src,),
        config=LintConfig(exclude=("src/generated",), base_dir=tmp_path),
    )
    assert files == (keep.resolve(),)


def test_discovery_handles_explicit_file_and_stable_order(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    first = src / "a.py"
    second = src / "b.py"
    first.write_text("x = 1\n", encoding="utf-8")
    second.write_text("x = 2\n", encoding="utf-8")

    files = discover_python_files(
        (second, src, first),
        config=LintConfig(base_dir=tmp_path),
    )
    assert files == (first.resolve(), second.resolve())


def test_discovery_default_excludes_are_applied_relative_to_root(tmp_path) -> None:
    project = tmp_path / "build" / "project"
    src = project / "src"
    src.mkdir(parents=True)
    module = src / "module.py"
    module.write_text("x = 1\n", encoding="utf-8")

    files = discover_python_files((project,), config=LintConfig(base_dir=project))
    assert files == (module.resolve(),)
