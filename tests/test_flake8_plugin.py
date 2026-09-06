import ast
from types import SimpleNamespace

from flake8_lint.plugin import ProjectRulesPlugin


def test_flake8_plugin_uses_shared_engine(tmp_path) -> None:
    ProjectRulesPlugin.parse_options(
        SimpleNamespace(
            select=("X002",),
            extend_select=(),
            ignore=(),
            extend_ignore=(),
            disable_noqa=False,
            flake8_lint_no_noqa=False,
        )
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        raise\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"), filename=str(sample))
    plugin = ProjectRulesPlugin(tree, str(sample))
    results = list(plugin.run())
    assert results == [
        (
            5,
            4,
            "X002 Do not use `except Exception:`; catch a more specific exception.",
            ProjectRulesPlugin,
        )
    ]


def test_flake8_plugin_respects_prefix_select_and_ignore(tmp_path) -> None:
    ProjectRulesPlugin.parse_options(
        SimpleNamespace(
            select=("X0",),
            extend_select=(),
            ignore=("X002",),
            extend_ignore=(),
            disable_noqa=False,
            flake8_lint_no_noqa=False,
        )
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        raise\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"), filename=str(sample))
    plugin = ProjectRulesPlugin(tree, str(sample))
    assert list(plugin.run()) == []


def test_flake8_plugin_respects_disable_noqa_option(tmp_path) -> None:
    ProjectRulesPlugin.parse_options(
        SimpleNamespace(
            select=("X002",),
            extend_select=(),
            ignore=(),
            extend_ignore=(),
            disable_noqa=True,
            flake8_lint_no_noqa=False,
        )
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:  # noqa: X002\n"
        "        raise\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"), filename=str(sample))
    plugin = ProjectRulesPlugin(tree, str(sample))
    results = list(plugin.run())
    assert len(results) == 1
    assert results[0][2].startswith("X002 ")


def test_flake8_plugin_disables_x_rules_when_flake8_selects_other_families(tmp_path) -> None:
    ProjectRulesPlugin.parse_options(
        SimpleNamespace(
            select=("E", "F"),
            extend_select=(),
            ignore=(),
            extend_ignore=(),
            disable_noqa=False,
            flake8_lint_no_noqa=False,
        )
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        raise\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"), filename=str(sample))
    plugin = ProjectRulesPlugin(tree, str(sample))
    assert list(plugin.run()) == []
