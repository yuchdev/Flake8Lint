import ast

from flake8_lint.plugin import ProjectRulesPlugin


def test_flake8_plugin_uses_shared_engine(tmp_path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def handler() -> int:\n"
        '    """Handle a broad exception."""\n'
        "    try:\n"
        "        risky()\n"
        "    except Exception:\n"
        "        return 1\n",
        encoding="utf-8",
    )
    tree = ast.parse(sample.read_text(encoding="utf-8"), filename=str(sample))
    plugin = ProjectRulesPlugin(tree, str(sample))
    results = list(plugin.run())
    assert results[0][2].startswith("X002 ")
