# flake8-lint examples

Each directory is a self-contained fixture project that demonstrates one facet
of configuration discovery, rule selection, `# noqa` handling, or the
custom-rule extension convention. Every directory ships an `expected.toml`
manifest describing the exact violation codes it should produce; that manifest
is read by `tests/test_examples.py` (it is **not** consumed by
`flake8_lint.config`).

Run any scenario by hand from the repository root, for example:

```bash
cd src/examples/canonical_flake8_lint_toml && flake8-lint check .
```

| Scenario                                              | What it proves                                                                                 | Run by hand                                                                 |
|-------------------------------------------------------|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`canonical_flake8_lint_toml`](canonical_flake8_lint_toml) | The canonical happy path: a `flake8_lint.toml` `select` narrows to a single code (`X002`).       | `cd src/examples/canonical_flake8_lint_toml && flake8-lint check .`         |
| [`legacy_pyproject_section`](legacy_pyproject_section) | The deprecated `[tool.flake8_lint_tests]` section still loads and emits a deprecation warning (`X001`). | `cd src/examples/legacy_pyproject_section && flake8-lint check .`           |
| [`pyproject_vs_toml_precedence`](pyproject_vs_toml_precedence) | A sibling `flake8_lint.toml` wins over `[tool.flake8_lint]` in `pyproject.toml` (`X002`, not `X001`). | `cd src/examples/pyproject_vs_toml_precedence && flake8-lint check .`       |
| [`custom_rule_module`](custom_rule_module)            | A project-local `USERNNN` rule module (`USER001`) loaded via `rule_modules`.                     | see note below                                                              |
| [`noqa_path_policy`](noqa_path_policy)                | `noqa_allowed` honours `# noqa` only under whitelisted paths (`X002` fires in `forbidden/` only). | `cd src/examples/noqa_path_policy && flake8-lint check allowed forbidden`   |
| [`cli_only`](cli_only)                                | A CLI-only project (no pytest wiring) that flags a missing docstring (`X005`).                   | `cd src/examples/cli_only && flake8-lint check .`                           |
| [`pytest_only`](pytest_only)                          | A pytest-only project using `assert_lint_clean` + `load_config` (`X009`).                        | `cd src/examples/pytest_only && python -m pytest test_lint.py`              |
| [`both_modes_parity`](both_modes_parity)              | CLI and pytest paths see the identical violation set (`X001`, `X002`).                           | `cd src/examples/both_modes_parity && flake8-lint check .`                  |

## Note on `custom_rule_module`

`custom_rule_module` loads a project-local rule module (`proj_rules.lint_rules`)
that must be importable. Two equivalent ways to run it:

- Standalone console script (needs the directory on the import path):

  ```bash
  cd src/examples/custom_rule_module && PYTHONPATH=. flake8-lint check .
  ```

- Module invocation (works out of the box, because `python -m` inserts the
  current directory as `sys.path[0]`):

  ```bash
  cd src/examples/custom_rule_module && python -m flake8_lint check .
  ```
