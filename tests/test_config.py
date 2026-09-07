from pathlib import Path

import pytest

from flake8_lint.config import (
    ConfigValidationError,
    LEGACY_SECTION_WARNING,
    LintConfig,
    load_config,
    validate_config,
)


def test_load_config_from_pyproject_section(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.flake8_lint]\n"
        'select = ["x002"]\n'
        "allow_noqa = false\n",
        encoding="utf-8",
    )
    config = load_config(cwd=tmp_path)
    assert config == LintConfig(select=("X002",), allow_noqa=False)
    assert config.base_dir == tmp_path


def test_load_config_falls_back_to_legacy_tests_section(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.flake8_lint_tests]\nignore = ["x003"]\n', encoding="utf-8")
    config = load_config(cwd=tmp_path)
    assert config.ignore == ("X003",)
    assert config.legacy_mode is True
    assert config.warnings == (LEGACY_SECTION_WARNING,)


def test_load_config_prefers_standalone_toml_over_pyproject(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.flake8_lint]\nselect = ["X001"]\n',
        encoding="utf-8",
    )
    (tmp_path / "flake8_lint.toml").write_text('select = ["X002"]\n', encoding="utf-8")
    config = load_config(cwd=tmp_path)
    assert config.select == ("X002",)


def test_load_config_searches_upward_without_merging(tmp_path) -> None:
    project = tmp_path / "project"
    nested = project / "pkg" / "subpkg"
    nested.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[tool.flake8_lint]\nselect = ["X002"]\n',
        encoding="utf-8",
    )
    config = load_config(cwd=nested)
    assert config.select == ("X002",)
    assert config.base_dir == project


def test_explicit_config_path_is_loaded_relative_to_cwd(tmp_path) -> None:
    configs = tmp_path / "configs"
    configs.mkdir()
    config_path = configs / "flake8_lint.toml"
    config_path.write_text('include = ["src"]\n', encoding="utf-8")
    cwd = tmp_path / "workspace"
    cwd.mkdir()
    config = load_config("..//configs/flake8_lint.toml", cwd=cwd)
    assert config.include == ("src",)
    assert config.base_dir == configs


def test_config_rejects_non_boolean_allow_noqa() -> None:
    with pytest.raises(ConfigValidationError):
        LintConfig.from_mapping({"allow_noqa": "false"})


def test_config_rejects_non_sequence_include_values() -> None:
    with pytest.raises(ConfigValidationError):
        LintConfig.from_mapping({"include": 1})


def test_config_rejects_string_include_values() -> None:
    with pytest.raises(ConfigValidationError):
        LintConfig.from_mapping({"include": "src"})


def test_config_rejects_non_string_sequence_items() -> None:
    with pytest.raises(ConfigValidationError):
        LintConfig.from_mapping({"ignore": [1]})


def test_validate_config_rejects_unknown_canonical_rule_selectors() -> None:
    with pytest.raises(ConfigValidationError, match="X999"):
        validate_config(LintConfig(select=("X001", "X999")), ("X001", "X002", "X003"))


def test_validate_config_keeps_known_reserved_x003() -> None:
    config = validate_config(LintConfig(ignore=("X003",)), ("X001", "X002", "X003"))
    assert config.ignore == ("X003",)


def test_validate_config_ignores_unknown_legacy_rules_with_warning() -> None:
    config = validate_config(
        LintConfig(select=("X001", "X999"), legacy_mode=True, warnings=(LEGACY_SECTION_WARNING,)),
        ("X001", "X002", "X003"),
    )
    assert config.select == ("X001",)
    assert any("X999" in warning for warning in config.warnings)


def test_merge_normalizes_code_prefixes_without_touching_path_fields() -> None:
    merged = LintConfig().merge(
        select=("x0",),
        ignore=("x002",),
        noqa_allowed=("src/example.py",),
    )
    assert merged.select == ("X0",)
    assert merged.ignore == ("X002",)
    assert merged.noqa_allowed == ("src/example.py",)
