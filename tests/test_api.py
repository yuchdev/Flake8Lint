import ast
import importlib
import os
import runpy
from pathlib import Path

import pytest

from flake8_lint import (
    RuleContext,
    RuleRegistry,
    RuleViolation,
    check_source,
    check_tree,
    lint_paths,
)
from flake8_lint.api import LintResult
from flake8_lint.config import ConfigValidationError, LintConfig


class DemoRule:
    code = "ORG001"
    description = "demo"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "demo violation")


def test_lint_result_ok_property() -> None:
    assert LintResult(violations=(), files_checked=1).ok is True


def test_check_tree_applies_select_to_custom_rules() -> None:
    registry = RuleRegistry()
    registry.register(DemoRule(), provider="tests.demo")
    tree = ast.parse("x = 1", filename="sample.py")
    config = LintConfig(select=("ORG",))
    violations = check_tree(tree, "sample.py", "x = 1\n", config=config, registry=registry)
    assert [violation.code for violation in violations] == ["ORG001"]


def test_check_tree_applies_ignore_to_custom_rules() -> None:
    registry = RuleRegistry()
    registry.register(DemoRule(), provider="tests.demo")
    tree = ast.parse("x = 1", filename="sample.py")
    violations = check_tree(
        tree,
        "sample.py",
        "x = 1\n",
        config=LintConfig(ignore=("ORG",)),
        registry=registry,
    )
    assert violations == ()


def test_check_tree_apply_noqa_false_ignores_matching_marker() -> None:
    source = "def f() -> int:\n    return 1\n"
    registry = RuleRegistry()
    registry.register(DemoRule(), provider="tests.demo")
    violations = check_tree(
        ast.parse(source, filename="sample.py"),
        "sample.py",
        "# noqa: ORG001\n",
        apply_noqa=False,
        config=LintConfig(select=("ORG001",)),
        registry=registry,
    )
    assert [violation.code for violation in violations] == ["ORG001"]


def test_check_tree_without_source_does_not_apply_noqa() -> None:
    registry = RuleRegistry()
    registry.register(DemoRule(), provider="tests.demo")
    violations = check_tree(
        ast.parse("x = 1", filename="sample.py"),
        "sample.py",
        None,
        config=LintConfig(select=("ORG001",)),
        registry=registry,
    )
    assert [violation.code for violation in violations] == ["ORG001"]


def test_check_source_accepts_rules_directly() -> None:
    violations = check_source(
        "x = 1\n",
        filename="sample.py",
        config=LintConfig(select=("ORG001",)),
        rules=[DemoRule()],
    )
    assert [violation.code for violation in violations] == ["ORG001"]


def test_check_source_rejects_unknown_selectors() -> None:
    with pytest.raises(ConfigValidationError):
        check_source("x = 1\n", filename="sample.py", config=LintConfig(select=("X999",)))


def test_lint_paths_defaults_to_src_and_tests_and_relativizes_output(tmp_path) -> None:
    src = tmp_path / "src"
    tests = tmp_path / "tests"
    src.mkdir()
    tests.mkdir()
    ignored = tmp_path / "pkg"
    ignored.mkdir()
    (src / "bad.py").write_text("def handler():\n    return 1\n", encoding="utf-8")
    (tests / "clean.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    (ignored / "also_bad.py").write_text("def nope():\n    return 1\n", encoding="utf-8")

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        result = lint_paths(config=LintConfig(select=("X007",), base_dir=tmp_path))
    finally:
        os.chdir(cwd)

    assert result.files_checked == 2
    assert [violation.filename for violation in result.violations] == ["src/bad.py"]


def test_lint_paths_uses_include_roots_when_no_paths_are_passed(tmp_path) -> None:
    project = tmp_path / "project"
    config_dir = project / "config"
    src = project / "src"
    config_dir.mkdir(parents=True)
    src.mkdir()
    (src / "bad.py").write_text("def handler():\n    return 1\n", encoding="utf-8")

    cwd = Path.cwd()
    try:
        os.chdir(project)
        result = lint_paths(
            config=LintConfig(
                base_dir=config_dir,
                include=("../src",),
                select=("X007",),
            )
        )
    finally:
        os.chdir(cwd)

    assert result.files_checked == 1
    assert [violation.filename for violation in result.violations] == ["src/bad.py"]


def test_lint_paths_explicit_paths_override_include_filters(tmp_path) -> None:
    project = tmp_path / "project"
    external = tmp_path / "external.py"
    project.mkdir()
    external.write_text("def handler():\n    return 1\n", encoding="utf-8")

    cwd = Path.cwd()
    try:
        os.chdir(project)
        result = lint_paths(
            paths=(external,),
            config=LintConfig(
                base_dir=project,
                include=("src/**/*.py",),
                select=("X007",),
            ),
        )
    finally:
        os.chdir(cwd)

    assert result.files_checked == 1
    assert [violation.filename for violation in result.violations] == [str(external)]


def test_package_version_falls_back_when_distribution_metadata_is_missing(monkeypatch) -> None:
    from importlib import metadata

    import flake8_lint

    def missing_version(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", missing_version)
    reloaded = importlib.reload(flake8_lint)
    assert reloaded.__version__ == "1.0.0"


def test_python_m_entry_point_raises_system_exit(monkeypatch) -> None:
    monkeypatch.setattr("flake8_lint.cli.main", lambda: 7)
    with pytest.raises(SystemExit, match="7"):
        runpy.run_module("flake8_lint.__main__", run_name="__main__")
