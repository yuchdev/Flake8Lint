import ast
import shutil
import subprocess
import sys
from pathlib import Path

from flake8_lint import RuleContext, RuleViolation, check_source, lint_paths
from flake8_lint.config import LintConfig

_EXAMPLES_DIR = Path(__file__).parents[1] / "src" / "examples"


def _console_script_cmd() -> list[str]:
    """Return the flake8-lint invocation, falling back to ``python -m flake8_lint``."""
    if shutil.which("flake8-lint") is not None:
        return ["flake8-lint"]
    return [sys.executable, "-m", "flake8_lint"]


class NoPrintRule:
    code = "ACME001"
    description = "Do not call print() in production code."

    def check(self, context: RuleContext):
        for node in ast.walk(context.tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                yield RuleViolation(
                    context.filename,
                    node.lineno,
                    node.col_offset,
                    self.code,
                    self.description,
                )


def test_custom_rule_docs_example_unit_flow() -> None:
    violations = check_source(
        'print("hello")\n',
        filename="example.py",
        config=LintConfig(select=("ACME001",)),
        rules=[NoPrintRule()],
    )
    assert [violation.code for violation in violations] == ["ACME001"]


def test_custom_rule_docs_example_lint_paths_flow(tmp_path) -> None:
    package = tmp_path / "my_project"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "lint_rules.py").write_text(
        "import ast\n"
        "from flake8_lint import RuleContext, RuleRegistry, RuleViolation\n\n"
        "class NoPrintRule:\n"
        '    code = "ACME001"\n'
        '    description = "Do not call print() in production code."\n\n'
        "    def check(self, context: RuleContext):\n"
        "        for node in ast.walk(context.tree):\n"
        "            if (\n"
        "                isinstance(node, ast.Call)\n"
        "                and isinstance(node.func, ast.Name)\n"
        '                and node.func.id == "print"\n'
        "            ):\n"
        "                yield RuleViolation(\n"
        "                    context.filename,\n"
        "                    node.lineno,\n"
        "                    node.col_offset,\n"
        "                    self.code,\n"
        "                    self.description,\n"
        "                )\n\n"
        "def register_rules(registry: RuleRegistry) -> None:\n"
        '    registry.register(NoPrintRule(), provider="my_project.lint_rules")\n',
        encoding="utf-8",
    )
    sample = tmp_path / "src"
    sample.mkdir()
    (sample / "example.py").write_text('print("hello")\n', encoding="utf-8")

    sys.path.insert(0, str(tmp_path))
    try:
        result = lint_paths(
            [sample],
            config=LintConfig(select=("ACME001",), rule_modules=("my_project.lint_rules",)),
        )
    finally:
        sys.path.remove(str(tmp_path))

    assert [violation.code for violation in result.violations] == ["ACME001"]


def test_installed_console_script_checks_cli_only_scenario() -> None:
    """Prove the real installed entry point works end-to-end, not just the library.

    Runs the actual ``flake8-lint`` console script (or falls back to
    ``python -m flake8_lint``) against the ``cli_only`` example fixture and
    asserts the expected violation code ``X005`` is reported with exit code 1.
    """
    scenario_dir = _EXAMPLES_DIR / "cli_only"
    cmd = [*_console_script_cmd(), "check", "."]
    proc = subprocess.run(cmd, cwd=str(scenario_dir), capture_output=True, text=True)

    assert proc.returncode == 1, (
        f"Expected exit code 1 from {cmd} in {scenario_dir.name}, "
        f"got {proc.returncode}.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "X005" in proc.stdout, (
        f"Expected X005 in stdout from {cmd} in {scenario_dir.name}.\nstdout: {proc.stdout!r}"
    )


def test_pytest_helper_failure_message_surfaces_violation_codes() -> None:
    """Prove that assert_lint_clean's failure message is legible in a real pytest run.

    Runs the embedded ``test_lint.py`` inside ``both_modes_parity`` as an
    isolated subprocess.  When violations exist, pytest captures the
    ``AssertionError`` message from :func:`flake8_lint.testing.assert_lint_clean`
    and writes it to stdout.  If the formatting ever regresses (empty message,
    missing codes, etc.) this test catches it before the on-call engineer hits
    the cryptic failure in production CI.
    """
    scenario_dir = _EXAMPLES_DIR / "both_modes_parity"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(scenario_dir), "-q"],
        capture_output=True,
        text=True,
    )

    assert proc.returncode != 0, (
        "Expected pytest to fail for both_modes_parity (app.py has X001 and X002 violations), "
        f"but it returned {proc.returncode}.\nstdout: {proc.stdout}"
    )
    assert "X001" in proc.stdout or "X002" in proc.stdout, (
        "Expected at least one of X001 or X002 to appear in pytest stdout, "
        "confirming assert_lint_clean's failure message is surfaced correctly.\n"
        f"stdout: {proc.stdout!r}"
    )
