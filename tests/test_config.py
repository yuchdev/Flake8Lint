import pytest

from flake8_lint.config import LintConfig, load_config


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


def test_load_config_falls_back_to_legacy_tests_section(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.flake8_lint_tests]\nignore = ["x003"]\n', encoding="utf-8")
    config = load_config(cwd=tmp_path)
    assert config.ignore == ("X003",)


def test_config_rejects_non_boolean_allow_noqa() -> None:
    with pytest.raises(TypeError):
        LintConfig.from_mapping({"allow_noqa": "false"})


def test_config_rejects_non_sequence_include_values() -> None:
    with pytest.raises(TypeError):
        LintConfig.from_mapping({"include": 1})


def test_config_rejects_non_string_sequence_items() -> None:
    with pytest.raises(TypeError):
        LintConfig.from_mapping({"ignore": [1]})
