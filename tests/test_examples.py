"""Discovery-driven parametrized test suite for src/examples/ scenarios.

Each subdirectory under ``src/examples/`` that carries an ``expected.toml``
sidecar is a self-contained fixture.  The sidecar declares:

* ``mode``             - ``"cli"`` | ``"pytest"`` | ``"both"``
* ``paths``            - list of paths relative to the scenario directory
* ``exit_code``        - expected linter exit code (0 = clean, 1 = violations)
* ``violation_codes``  - exact sorted set of rule codes that must be reported
* ``warnings_contain`` - (optional) substrings expected somewhere in stderr
* ``rule_modules``     - (optional) importable modules with extra rules; when
                         present the scenario dir is prepended to sys.path
                         before the in-process CLI call.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Optional

import pytest

EXAMPLES_DIR = Path(__file__).parents[1] / "src" / "examples"


def _discover_scenarios() -> list[tuple[Path, dict[str, Any]]]:
    """Return ``(scenario_dir, expected_data)`` pairs for every ``expected.toml``."""
    results: list[tuple[Path, dict[str, Any]]] = []
    for candidate in sorted(EXAMPLES_DIR.iterdir()):
        if not candidate.is_dir():
            continue
        expected_path = candidate / "expected.toml"
        if not expected_path.is_file():
            continue
        expected: dict[str, Any] = tomllib.loads(expected_path.read_text(encoding="utf-8"))
        results.append((candidate, expected))
    return results


_SCENARIOS = _discover_scenarios()
_SCENARIO_IDS = [scenario_dir.name for scenario_dir, _ in _SCENARIOS]


def _run_cli_check(
    scenario_dir: Path,
    expected: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> int:
    """Run an in-process CLI ``check`` for *scenario_dir* and assert codes/warnings.

    :param scenario_dir: Root directory of the scenario fixture.
    :param expected: Parsed ``expected.toml`` data.
    :param capsys: pytest capsys fixture for capturing stdout/stderr.
    :returns: The exit code returned by :func:`flake8_lint.cli.main`.
    """
    from flake8_lint.cli import main

    paths: list[str] = expected["paths"]
    expected_exit_code: int = expected["exit_code"]
    expected_codes: set[str] = set(expected["violation_codes"])
    warnings_contain: list[str] = expected.get("warnings_contain", [])
    rule_modules: list[str] = expected.get("rule_modules", [])

    original_cwd = Path.cwd()
    path_inserted = False
    if rule_modules:
        sys.path.insert(0, str(scenario_dir))
        path_inserted = True

    try:
        os.chdir(scenario_dir)
        cli_rc = main(["check", "--output-format", "json", *paths])
    finally:
        os.chdir(original_cwd)
        if path_inserted:
            sys.path.remove(str(scenario_dir))

    captured = capsys.readouterr()
    assert cli_rc == expected_exit_code, (
        f"Scenario {scenario_dir.name!r}: expected exit code {expected_exit_code}, "
        f"got {cli_rc}.\nstdout: {captured.out}\nstderr: {captured.err}"
    )

    payload: dict[str, Any] = json.loads(captured.out)
    actual_codes: set[str] = {v["code"] for v in payload["violations"]}
    assert actual_codes == expected_codes, (
        f"Scenario {scenario_dir.name!r}: expected violation codes {sorted(expected_codes)}, "
        f"got {sorted(actual_codes)}"
    )

    for substring in warnings_contain:
        assert substring in captured.err, (
            f"Scenario {scenario_dir.name!r}: expected substring {substring!r} in stderr.\n"
            f"stderr was: {captured.err!r}"
        )

    return cli_rc


def _run_pytest_subprocess(scenario_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run pytest on *scenario_dir* in a fresh subprocess.

    :param scenario_dir: Scenario directory containing ``test_lint.py``.
    :returns: The completed subprocess result.
    """
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(scenario_dir), "-q"],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("scenario_dir,expected", _SCENARIOS, ids=_SCENARIO_IDS)
def test_example(
    scenario_dir: Path,
    expected: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run each scenario fixture in the mode declared by its ``expected.toml``.

    * ``"cli"``    - in-process CLI check; assert exit code, violation codes, and
                     optional warning substrings.
    * ``"pytest"`` - subprocess ``python -m pytest`` on the scenario dir; the
                     embedded ``test_lint.py`` fails when violations exist and
                     passes when the code is clean.
    * ``"both"``   - both the CLI check and the pytest subprocess check; asserts
                     that their exit-code truthiness agrees (parity guarantee).
    """
    mode: str = expected["mode"]
    exit_code: int = expected["exit_code"]
    expects_violations = exit_code != 0

    if mode == "cli":
        _run_cli_check(scenario_dir, expected, capsys)

    elif mode == "pytest":
        proc = _run_pytest_subprocess(scenario_dir)
        assert (proc.returncode != 0) == expects_violations, (
            f"Scenario {scenario_dir.name!r}: pytest subprocess returned {proc.returncode}; "
            f"expected {'failure' if expects_violations else 'success'}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

    elif mode == "both":
        cli_rc = _run_cli_check(scenario_dir, expected, capsys)
        proc = _run_pytest_subprocess(scenario_dir)
        # Parity guarantee: both modes must agree on whether violations are present.
        assert (cli_rc != 0) == (proc.returncode != 0), (
            f"Scenario {scenario_dir.name!r}: CLI exit code {cli_rc} and pytest "
            f"subprocess exit code {proc.returncode} disagree on violation presence.\n"
            f"pytest stdout: {proc.stdout}\npytest stderr: {proc.stderr}"
        )

    else:
        raise ValueError(f"Unknown mode {mode!r} in {scenario_dir / 'expected.toml'}")


def _get_optional_scenario(name: str) -> Optional[Path]:
    """Return the path to a named scenario dir, or ``None`` when absent."""
    candidate = EXAMPLES_DIR / name
    return candidate if candidate.is_dir() else None
