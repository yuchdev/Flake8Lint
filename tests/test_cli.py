import json
import os
import textwrap
from pathlib import Path

from flake8_lint.cli import main


def test_cli_version(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "flake8-lint 1.0.0"


def test_cli_check_json_reports_violation(tmp_path, capsys) -> None:
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
    assert main(["check", str(sample), "--select", "X002", "--output-format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["files_checked"] == 1
    assert payload["violations"][0]["code"] == "X002"


def test_cli_text_uses_relative_paths_and_exit_zero(tmp_path, capsys) -> None:
    src = tmp_path / "src"
    src.mkdir()
    sample = src / "sample.py"
    sample.write_text(
        'def documented() -> int:\n    """Return a number."""\n    return 1\n',
        encoding="utf-8",
    )
    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        assert main(["check"]) == 0
    finally:
        os.chdir(cwd)
    assert capsys.readouterr().out.strip() == "Checked 1 file(s); no violations found."


def test_cli_errors_are_reported_on_stderr(capsys) -> None:
    assert main(["check", "--rule-module", "missing.module", "."]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "missing.module" in captured.err


def test_cli_uses_explicit_config_and_rule_module(tmp_path, monkeypatch, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config_dir = project / "config"
    config_dir.mkdir()
    package = project / "demo_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            from flake8_lint import RuleRegistry, RuleViolation

            class LocalRule:
                code = "ORG001"
                description = "Local rule"

                def check(self, context):
                    yield RuleViolation(context.filename, 1, 0, self.code, "local rule")

            def register_rules(registry: RuleRegistry) -> None:
                registry.register(LocalRule(), provider="demo_project.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "flake8_lint.toml").write_text(
        'include = ["../src"]\nselect = ["ORG001"]\n',
        encoding="utf-8",
    )
    src = project / "src"
    src.mkdir()
    sample = src / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(project))

    cwd = Path.cwd()
    try:
        os.chdir(project)
        assert (
            main(
                [
                    "check",
                    "--config",
                    "config/flake8_lint.toml",
                    "--rule-module",
                    "demo_project.lint_rules",
                    ".",
                ]
            )
            == 1
        )
    finally:
        os.chdir(cwd)
    captured = capsys.readouterr()
    assert "src/sample.py:1:0: ORG001 local rule" in captured.out


def test_cli_warns_for_legacy_config_and_invalid_canonical_config(tmp_path, capsys) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "pyproject.toml").write_text(
        '[tool.flake8_lint_tests]\nselect = ["X001", "X999"]\n',
        encoding="utf-8",
    )
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    (canonical / "pyproject.toml").write_text(
        '[tool.flake8_lint]\nselect = ["X001", "X999"]\n',
        encoding="utf-8",
    )
    sample = "def documented() -> int:\n    \"\"\"Return a number.\"\"\"\n    return 1\n"
    (legacy / "sample.py").write_text(sample, encoding="utf-8")
    (canonical / "sample.py").write_text(sample, encoding="utf-8")

    cwd = Path.cwd()
    try:
        os.chdir(legacy)
        assert main(["check", "sample.py"]) == 0
        legacy_capture = capsys.readouterr()
        assert "deprecated" in legacy_capture.err
        assert "X999" in legacy_capture.err

        os.chdir(canonical)
        assert main(["check", "sample.py"]) == 2
        canonical_capture = capsys.readouterr()
        assert "Unknown select rule selector(s): X999" in canonical_capture.err
    finally:
        os.chdir(cwd)


def test_cli_no_rule_plugins_disables_installed_provider(monkeypatch, tmp_path, capsys) -> None:
    class FakeEntryPoint:
        name = "demo"
        value = "demo_rules:register_rules"
        dist = None

        def load(self):
            def register_rules(registry):
                from flake8_lint import RuleViolation

                class PluginRule:
                    code = "ZZZ001"
                    description = "provider rule"

                    def check(self, context):
                        yield RuleViolation(context.filename, 1, 0, self.code, "provider rule")

                registry.register(PluginRule(), provider="demo_rules")

            return register_rules

    class FakeEntryPoints(list):
        def select(self, *, group: str):
            assert group == "flake8_lint.rules"
            return self

    monkeypatch.setattr(
        "flake8_lint.registry.metadata.entry_points",
        lambda: FakeEntryPoints([FakeEntryPoint()]),
    )
    sample = tmp_path / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")

    assert main(["check", str(sample), "--select", "ZZZ"]) == 1
    assert "ZZZ001" in capsys.readouterr().out
    assert main(["check", str(sample), "--select", "ZZZ", "--no-rule-plugins"]) == 2
    assert "Unknown select rule selector(s): ZZZ" in capsys.readouterr().err


def test_cli_select_and_ignore_override_loaded_config(tmp_path, capsys) -> None:
    (tmp_path / "flake8_lint.toml").write_text(
        'select = ["X999"]\nignore = ["X001"]\n',
        encoding="utf-8",
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )

    cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        assert main(["check", "--select", "X001", "--ignore", "X002", "sample.py"]) == 1
    finally:
        os.chdir(cwd)

    captured = capsys.readouterr()
    assert "X001" in captured.out
    assert "Unknown select rule selector(s): X999" not in captured.err
