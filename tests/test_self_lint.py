"""Self-lint tests: prove flakeforge checks itself with itself.

These tests verify two requirements:
1. The package source (src/flakeforge/) is clean under its own rules.
2. A bare ``check .`` from the repo root uses the ``include`` scoping from
   ``pyproject.toml`` and skips ``tests/samples/`` and ``src/examples/``
   automatically - the same invocation CI would run.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
PACKAGE_DIR = REPO_ROOT / "src" / "flakeforge"


def test_self_lint_api() -> None:
    """API-level: real config from repo root, lint the package, assert zero violations.

    A regression here immediately lists every offending location so the on-call
    engineer does not have to re-run the linter manually to find the culprit.
    """
    from flakeforge.api import lint_paths
    from flakeforge.config import load_config

    config = load_config(cwd=REPO_ROOT)
    result = lint_paths([PACKAGE_DIR], config=config)

    if not result.ok:
        lines = [f"{v.filename}:{v.lineno}:{v.col_offset}: {v.code} {v.message}" for v in result.violations]
        raise AssertionError("flakeforge self-check found violations in src/flakeforge/:\n" + "\n".join(lines))


def test_self_lint_cli_include_scoping() -> None:
    """CLI-level: ``check .`` from repo root auto-scopes to include= and exits 0.

    Proves that the ``include = ["src/flakeforge"]`` entry in ``pyproject.toml``
    causes a bare invocation to skip ``tests/samples/`` (which deliberately
    contain rule violations) and ``src/examples/`` without requiring the caller
    to pass an explicit path.  This is exactly what CI runs.
    """
    from flakeforge.cli import main

    original_cwd = Path.cwd()
    try:
        os.chdir(REPO_ROOT)
        exit_code = main(["check", "."])
    finally:
        os.chdir(original_cwd)

    assert exit_code == 0, (
        f"flakeforge check . from repo root returned exit code {exit_code}; "
        "expected 0. The include= scoping should restrict linting to src/flakeforge/ "
        "so that tests/samples/ and src/examples/ are not checked."
    )
