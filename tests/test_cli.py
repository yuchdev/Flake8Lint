import json
import textwrap

import pytest

from flakeforge.cli import main


def test_cli_version(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "flakeforge 1.0.0"


def test_cli_check_json_reports_violation(tmp_path, monkeypatch, capsys) -> None:
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
    monkeypatch.chdir(tmp_path)
    assert main(["check", str(sample), "--select", "X002", "--output-format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["files_checked"] == 1
    assert payload["violations"][0]["code"] == "X002"


def test_cli_text_uses_relative_paths_and_exit_zero(tmp_path, monkeypatch, capsys) -> None:
    src = tmp_path / "src"
    src.mkdir()
    sample = src / "sample.py"
    sample.write_text(
        'def documented() -> int:\n    """Return a number."""\n    return 1\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 0
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
            from flakeforge import RuleRegistry, RuleViolation

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
    (config_dir / "flakeforge.toml").write_text(
        'include = ["../src"]\nselect = ["ORG001"]\n',
        encoding="utf-8",
    )
    src = project / "src"
    src.mkdir()
    sample = src / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(project))

    monkeypatch.chdir(project)
    assert (
        main(
            [
                "check",
                "--config",
                "config/flakeforge.toml",
                "--rule-module",
                "demo_project.lint_rules",
                ".",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "src/sample.py:1:0: ORG001 local rule" in captured.out


def test_cli_warns_for_legacy_config_and_invalid_canonical_config(tmp_path, monkeypatch, capsys) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "pyproject.toml").write_text(
        '[tool.flake8_lint]\nselect = ["X001", "X999"]\n',
        encoding="utf-8",
    )
    canonical = tmp_path / "canonical"
    canonical.mkdir()
    (canonical / "pyproject.toml").write_text(
        '[tool.flakeforge]\nselect = ["X001", "X999"]\n',
        encoding="utf-8",
    )
    sample = 'def documented() -> int:\n    """Return a number."""\n    return 1\n'
    (legacy / "sample.py").write_text(sample, encoding="utf-8")
    (canonical / "sample.py").write_text(sample, encoding="utf-8")

    monkeypatch.chdir(legacy)
    assert main(["check", "sample.py"]) == 0
    legacy_capture = capsys.readouterr()
    assert "deprecated" in legacy_capture.err
    assert "X999" in legacy_capture.err

    monkeypatch.chdir(canonical)
    assert main(["check", "sample.py"]) == 2
    canonical_capture = capsys.readouterr()
    assert "Unknown select rule selector(s): X999" in canonical_capture.err


def test_cli_no_rule_plugins_disables_installed_provider(monkeypatch, tmp_path, capsys) -> None:
    class FakeEntryPoint:
        name = "demo"
        value = "demo_rules:register_rules"
        dist = None

        def load(self):
            def register_rules(registry):
                from flakeforge import RuleViolation

                class PluginRule:
                    code = "ZZZ001"
                    description = "provider rule"

                    def check(self, context):
                        yield RuleViolation(context.filename, 1, 0, self.code, "provider rule")

                registry.register(PluginRule(), provider="demo_rules")

            return register_rules

    class FakeEntryPoints(list):
        def select(self, *, group: str):
            if group != "flakeforge.rules":
                raise ValueError(f"unexpected entry-point group: {group!r}")
            return self

    monkeypatch.setattr(
        "flakeforge.registry.metadata.entry_points",
        lambda: FakeEntryPoints([FakeEntryPoint()]),
    )
    sample = tmp_path / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", str(sample), "--select", "ZZZ"]) == 1
    assert "ZZZ001" in capsys.readouterr().out
    assert main(["check", str(sample), "--select", "ZZZ", "--no-rule-plugins"]) == 2
    assert "Unknown select rule selector(s): ZZZ" in capsys.readouterr().err


def test_cli_honors_target_config_when_run_from_outside(tmp_path, monkeypatch, capsys) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "flakeforge.toml").write_text('ignore = ["X001"]\n', encoding="utf-8")
    sample = project / "sample.py"
    sample.write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )
    outside = tmp_path / "elsewhere"
    outside.mkdir()

    monkeypatch.chdir(outside)
    # The target project ignores X001, so linting it is clean even though
    # the invocation runs from an unrelated working directory.
    assert main(["check", "--select", "X001", str(project)]) == 0

    captured = capsys.readouterr()
    assert "X001" not in captured.out
    assert captured.out.strip() == "Checked 1 file(s); no violations found."


def test_cli_select_and_ignore_override_loaded_config(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text(
        'select = ["X999"]\nignore = ["X001"]\n',
        encoding="utf-8",
    )
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--select", "X001", "--ignore", "X002", "sample.py"]) == 1

    captured = capsys.readouterr()
    assert "X001" in captured.out
    assert "Unknown select rule selector(s): X999" not in captured.err


def test_cli_nonexistent_path_is_invalid_invocation(tmp_path, capsys) -> None:
    missing = tmp_path / "does-not-exist"

    assert main(["check", str(missing)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"flakeforge: path does not exist: {missing}" in captured.err


def test_cli_no_config_ignores_hostile_toml(tmp_path, monkeypatch, capsys) -> None:
    # Acceptance: --no-config must not honour the on-disk ignore = ["X"].
    (tmp_path / "flakeforge.toml").write_text('ignore = ["X"]\n', encoding="utf-8")
    sample = tmp_path / "sample.py"
    sample.write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--no-config", "--select", "X001", "."]) == 1
    assert "X001" in capsys.readouterr().out


def test_cli_no_config_skips_project_rule_modules(tmp_path, monkeypatch, capsys) -> None:
    # A hostile config file's rule_modules must not load under --no-config (C7).
    (tmp_path / "flakeforge.toml").write_text('rule_modules = ["nonexistent.module"]\n', encoding="utf-8")
    sample = tmp_path / "sample.py"
    sample.write_text('def g() -> int:\n    """Doc."""\n    return 1\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--no-config", "."]) == 0
    assert capsys.readouterr().out.strip() == "Checked 1 file(s); no violations found."


def test_cli_include_replaces_config_list(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('include = ["only"]\n', encoding="utf-8")
    keep = tmp_path / "pkg"
    keep.mkdir()
    (keep / "sample.py").write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    # --include replaces the file's ["only"] whitelist with pkg/*.
    assert main(["check", "--include", "pkg/*", "--select", "X001", "."]) == 1
    assert "pkg/sample.py" in capsys.readouterr().out


def test_cli_exclude_replaces_config_list(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('exclude = ["pkg"]\n', encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "sample.py").write_text(
        "def f():\n    try:\n        run()\n    except:\n        return 1\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    # --exclude replaces the file's ["pkg"], so pkg is scanned and flagged.
    assert main(["check", "--exclude", "vendor", "--select", "X001", "."]) == 1
    assert "pkg/sample.py" in capsys.readouterr().out


def test_cli_config_and_no_config_are_mutually_exclusive(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text("select = []\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        main(["check", "--config", "flakeforge.toml", "--no-config", "."])
    assert excinfo.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


_BROAD_EXCEPT = (
    "def handler() -> int:\n"
    '    """Handle a broad exception."""\n'
    "    try:\n"
    "        risky()\n"
    "    except Exception:\n"
    "        return 1\n"
)


def test_cli_output_format_json_from_config_file(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('output_format = "json"\n', encoding="utf-8")
    (tmp_path / "sample.py").write_text(_BROAD_EXCEPT, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--select", "X002", "sample.py"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["violations"][0]["code"] == "X002"


def test_cli_output_format_cli_overrides_config_to_text(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('output_format = "json"\n', encoding="utf-8")
    (tmp_path / "sample.py").write_text(_BROAD_EXCEPT, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--select", "X002", "--output-format", "text", "sample.py"]) == 1
    out = capsys.readouterr().out
    assert out.lstrip().startswith("sample.py:")


def test_cli_output_format_cli_overrides_config_to_json(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('output_format = "text"\n', encoding="utf-8")
    (tmp_path / "sample.py").write_text(_BROAD_EXCEPT, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--select", "X002", "--output-format", "json", "sample.py"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["violations"][0]["code"] == "X002"


def test_cli_invalid_output_format_in_config_is_exit_2(tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "flakeforge.toml").write_text('output_format = "xml"\n', encoding="utf-8")
    (tmp_path / "sample.py").write_text(_BROAD_EXCEPT, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", "--select", "X002", "sample.py"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Unknown output format" in captured.err


def _entry_points_with_zzz(monkeypatch) -> None:
    class FakeEntryPoint:
        name = "demo"
        value = "demo_rules:register_rules"
        dist = None

        def load(self):
            def register_rules(registry):
                from flakeforge import RuleViolation

                class PluginRule:
                    code = "ZZZ001"
                    description = "provider rule"

                    def check(self, context):
                        yield RuleViolation(context.filename, 1, 0, self.code, "provider rule")

                registry.register(PluginRule(), provider="demo_rules")

            return register_rules

    class FakeEntryPoints(list):
        def select(self, *, group: str):
            if group != "flakeforge.rules":
                raise ValueError(f"unexpected entry-point group: {group!r}")
            return self

    monkeypatch.setattr(
        "flakeforge.registry.metadata.entry_points",
        lambda: FakeEntryPoints([FakeEntryPoint()]),
    )


def test_cli_rule_plugins_false_in_config_disables_provider(monkeypatch, tmp_path, capsys) -> None:
    _entry_points_with_zzz(monkeypatch)
    (tmp_path / "flakeforge.toml").write_text("rule_plugins = false\n", encoding="utf-8")
    sample = tmp_path / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    # The provider that owns ZZZ is not loaded, so selecting it is invalid.
    assert main(["check", str(sample), "--select", "ZZZ"]) == 2
    assert "Unknown select rule selector(s): ZZZ" in capsys.readouterr().err
    # A CLI --rule-plugins overrides the file's false in the other direction.
    assert main(["check", str(sample), "--select", "ZZZ", "--rule-plugins"]) == 1
    assert "ZZZ001" in capsys.readouterr().out


def test_cli_no_rule_plugins_overrides_config_true(monkeypatch, tmp_path, capsys) -> None:
    _entry_points_with_zzz(monkeypatch)
    (tmp_path / "flakeforge.toml").write_text("rule_plugins = true\n", encoding="utf-8")
    sample = tmp_path / "sample.py"
    sample.write_text("x = 1\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert main(["check", str(sample), "--select", "ZZZ", "--no-rule-plugins"]) == 2
    assert "Unknown select rule selector(s): ZZZ" in capsys.readouterr().err
