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
