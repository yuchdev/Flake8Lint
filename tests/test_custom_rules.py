import os
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from flakeforge import RuleContext, RuleRegistry, RuleViolation, check_source
from flakeforge.config import LintConfig
from flakeforge.registry import (
    DuplicateRuleCodeError,
    InvalidRuleCodeError,
    RuleProviderLoadError,
    resolve_registry,
)


class LocalRule:
    code = "ORG001"
    description = "Local rule"

    def check(self, context: RuleContext):
        yield RuleViolation(context.filename, 1, 0, self.code, "local rule")


def test_direct_rule_registration_and_filtering() -> None:
    registry = RuleRegistry()
    registry.register(LocalRule(), provider="tests.local")
    assert [violation.code for violation in check_source("x = 1\n", rules=[LocalRule()])] == ["ORG001"]
    assert check_source("x = 1\n", config=LintConfig(ignore=("ORG",)), rules=[LocalRule()]) == ()


def test_project_local_rule_module_registers_rules(tmp_path, monkeypatch) -> None:
    package = tmp_path / "demo_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            from flakeforge import RuleRegistry, RuleViolation

            class NoPrintRule:
                code = "ORG001"
                description = "Local rule"

                def check(self, context):
                    yield RuleViolation(context.filename, 1, 0, self.code, "local rule")

            def register_rules(registry: RuleRegistry) -> None:
                registry.register(NoPrintRule(), provider="demo_project.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = resolve_registry(
        rule_modules=("demo_project.lint_rules",),
        include_entry_points=False,
    )
    violations = check_source(
        "x = 1\n",
        filename="demo.py",
        config=LintConfig(select=("ORG001",)),
        registry=registry,
    )
    assert [violation.code for violation in violations] == ["ORG001"]


def test_missing_rule_module_reports_module_name(tmp_path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(RuleProviderLoadError, match="missing\\.module"):
        resolve_registry(rule_modules=("missing.module",), include_entry_points=False)


def test_duplicate_rule_codes_fail_clearly(tmp_path, monkeypatch) -> None:
    package = tmp_path / "dup_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        textwrap.dedent(
            """
            class DuplicateRule:
                code = "X001"
                description = "duplicate"

                def check(self, context):
                    return ()

            def register_rules(registry):
                registry.register(DuplicateRule(), provider="dup_project.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(DuplicateRuleCodeError):
        resolve_registry(rule_modules=("dup_project.lint_rules",), include_entry_points=False)


def test_invalid_rule_code_fails_clearly() -> None:
    class BadRule:
        code = "org1"
        description = "bad"

        def check(self, context):
            return ()

    registry = RuleRegistry()
    with pytest.raises(InvalidRuleCodeError):
        registry.register(BadRule(), provider="tests.bad")


def test_custom_noqa_suppresses_matching_rule() -> None:
    source = "x = 1  # noqa: ORG001\n"
    assert (
        check_source(
            source,
            filename="sample.py",
            config=LintConfig(select=("ORG001",), noqa_allowed=("sample.py",)),
            rules=[LocalRule()],
        )
        == ()
    )


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str
    value: str
    loader: object
    dist: Optional[object] = None

    def load(self):
        return self.loader


class FakeEntryPoints(list):
    def select(self, *, group: str):
        assert group == "flakeforge.rules"
        return self


def test_installed_provider_entry_points_are_loaded_deterministically(monkeypatch) -> None:
    def register_second(registry: RuleRegistry) -> None:
        class SecondRule:
            code = "ZZZ001"
            description = "second"

            def check(self, context):
                return ()

        registry.register(SecondRule(), provider="pkg.second")

    def register_first(registry: RuleRegistry) -> None:
        class FirstRule:
            code = "AAA001"
            description = "first"

            def check(self, context):
                return ()

        registry.register(FirstRule(), provider="pkg.first")

    monkeypatch.setattr(
        "flakeforge.registry.metadata.entry_points",
        lambda: FakeEntryPoints(
            [
                FakeEntryPoint("zzz", "pkg.second:register_rules", register_second),
                FakeEntryPoint("aaa", "pkg.first:register_rules", register_first),
            ]
        ),
    )
    registry = resolve_registry()
    assert registry.known_codes()[:2] == ("AAA001", "X001")
    assert "ZZZ001" in registry.known_codes()


def test_installed_provider_load_error_names_provider(monkeypatch) -> None:
    def boom(registry):
        del registry
        raise RuntimeError("broken provider")

    monkeypatch.setattr(
        "flakeforge.registry.metadata.entry_points",
        lambda: FakeEntryPoints([FakeEntryPoint("boom", "pkg.boom:register_rules", boom)]),
    )
    with pytest.raises(RuleProviderLoadError, match="boom"):
        resolve_registry()


def _write_rule_package(
    root: Path,
    package: str,
    *,
    code: str,
    body: str = "",
) -> str:
    """Create ``root/<package>/lint_rules.py`` and return its dotted module name."""
    directory = root / package
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "__init__.py").write_text("", encoding="utf-8")
    (directory / "lint_rules.py").write_text(
        textwrap.dedent(
            f"""
            from flakeforge import RuleRegistry, RuleViolation
            {body}

            class ProjectRule:
                code = "{code}"
                description = "Project rule"

                def check(self, context):
                    yield RuleViolation(context.filename, 1, 0, self.code, "project rule")

            def register_rules(registry: RuleRegistry) -> None:
                registry.register(ProjectRule(), provider="{package}.lint_rules")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return f"{package}.lint_rules"


def test_project_root_loads_uninstalled_module_from_foreign_cwd(tmp_path, monkeypatch) -> None:
    project = tmp_path / "project"
    module_name = _write_rule_package(project, "root_demo_project", code="ROOT001")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    # Run from an unrelated cwd; the module is not installed and not on sys.path.
    monkeypatch.chdir(elsewhere)
    assert str(project) not in sys.path

    registry = resolve_registry(
        rule_modules=(module_name,),
        include_entry_points=False,
        project_root=project,
    )

    assert "ROOT001" in registry.known_codes()


def test_project_root_restores_syspath_after_success(tmp_path) -> None:
    project = tmp_path / "ok_project"
    module_name = _write_rule_package(project, "restore_ok_project", code="ROOT002")
    before = list(sys.path)
    syspath_object = sys.path

    resolve_registry(
        rule_modules=(module_name,),
        include_entry_points=False,
        project_root=project,
    )

    assert sys.path == before
    assert sys.path is syspath_object


def test_project_root_restores_syspath_after_failure(tmp_path) -> None:
    project = tmp_path / "broken_project"
    project.mkdir()
    package = project / "broken_root_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text("raise RuntimeError('boom at import')\n", encoding="utf-8")
    before = list(sys.path)
    syspath_object = sys.path

    with pytest.raises(RuleProviderLoadError, match="broken_root_project"):
        resolve_registry(
            rule_modules=("broken_root_project.lint_rules",),
            include_entry_points=False,
            project_root=project,
        )

    assert sys.path == before
    assert sys.path is syspath_object


def test_load_error_message_names_module_and_base_dir(tmp_path) -> None:
    project = tmp_path / "named_project"
    project.mkdir()
    with pytest.raises(RuleProviderLoadError) as excinfo:
        resolve_registry(
            rule_modules=("no_such_module_here",),
            include_entry_points=False,
            project_root=project,
        )
    message = str(excinfo.value)
    assert "no_such_module_here" in message
    assert str(project.resolve()) in message


def test_none_project_root_does_not_insert_base_dir(tmp_path) -> None:
    project = tmp_path / "untrusted"
    module_name = _write_rule_package(project, "untrusted_project", code="ROOT003")
    # The directory is neither installed, on sys.path, nor the cwd.
    assert str(project) not in sys.path
    # With project_root=None the base_dir is never placed on sys.path, so a
    # module reachable only from that directory cannot be imported.
    with pytest.raises(RuleProviderLoadError, match="untrusted_project"):
        resolve_registry(
            rule_modules=(module_name,),
            include_entry_points=False,
            project_root=None,
        )


def test_target_module_named_like_stdlib_or_flakeforge_does_not_corrupt(tmp_path) -> None:
    project = tmp_path / "hostile_project"
    module_name = _write_rule_package(project, "hostile_root_project", code="ROOT004")
    # A repo shipping top-level modules named like stdlib / flakeforge, placed
    # first on sys.path while the rule module loads.
    (project / "os.py").write_text("raise RuntimeError('hostile os')\n", encoding="utf-8")
    (project / "flakeforge.py").write_text("raise RuntimeError('hostile flakeforge')\n", encoding="utf-8")
    real_os = sys.modules["os"]
    real_flakeforge = sys.modules["flakeforge"]

    registry = resolve_registry(
        rule_modules=(module_name,),
        include_entry_points=False,
        project_root=project,
    )

    assert "ROOT004" in registry.known_codes()
    # The already-imported stdlib / flakeforge modules were not shadowed.
    assert sys.modules["os"] is real_os
    assert sys.modules["flakeforge"] is real_flakeforge
    assert os.getcwd()
    # The linter's own registry still resolves built-ins afterward, in-process.
    assert "X001" in resolve_registry(include_entry_points=False).known_codes()


def test_project_root_accepts_symlinked_checkout_from_foreign_cwd(tmp_path, monkeypatch) -> None:
    project = tmp_path / "real_checkout"
    module_name = _write_rule_package(project, "symlink_root_project", code="ROOT005")
    link = tmp_path / "linked_checkout"
    try:
        link.symlink_to(project, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not supported on this platform")
    elsewhere = tmp_path / "away"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    registry = resolve_registry(
        rule_modules=(module_name,),
        include_entry_points=False,
        project_root=link,
    )

    assert "ROOT005" in registry.known_codes()


def test_rule_module_root_requires_a_loaded_config_file(tmp_path) -> None:
    assert LintConfig(base_dir=tmp_path).rule_module_root is None
    config_file = tmp_path / "flakeforge.toml"
    loaded = LintConfig(base_dir=tmp_path, config_path=config_file)
    assert loaded.rule_module_root == tmp_path
    assert loaded.merge(select=("X001",)).rule_module_root == tmp_path


def test_cli_rule_module_is_not_imported_from_target_without_config(tmp_path, monkeypatch, capsys) -> None:
    from flakeforge.cli import main

    project = tmp_path / "no_config_project"
    module_name = _write_rule_package(project, "shadow_project", code="ROOT005")
    (project / "example.py").write_text("value = 1\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    # No config file in or above the target: its directory must not go on
    # sys.path, so the explicit --rule-module cannot resolve from it.
    assert main(["check", "--rule-module", module_name, str(project)]) == 2
    assert "shadow_project" in capsys.readouterr().err
    assert str(project) not in sys.path


def test_cli_no_config_rule_module_is_not_imported_from_target(tmp_path, monkeypatch, capsys) -> None:
    from flakeforge.cli import main

    project = tmp_path / "no_config_flag_project"
    module_name = _write_rule_package(project, "no_config_shadow_project", code="ROOT006")
    (project / "example.py").write_text("value = 1\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    # --no-config forbids loading any config file, so no config-derived root can
    # place the target directory on sys.path; the explicit --rule-module must
    # therefore fail to resolve rather than importing from the target.
    assert main(["check", "--no-config", "--rule-module", module_name, str(project)]) == 2
    assert "no_config_shadow_project" in capsys.readouterr().err
    assert str(project) not in sys.path
