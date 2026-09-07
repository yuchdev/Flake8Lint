# flake8-lint

Reusable AST-based Python lint rules with a standalone CLI, a thin Flake8 adapter, and an explicit pytest helper.

## Purpose

`flake8-lint` extracts custom AST-based project rules into a reusable package without coupling the rule engine to a single application repository.

## Installation

```bash
pip install flake8-lint
```

For development:

```bash
pip install -e .[dev]
```

## CLI

```bash
flake8-lint --version
flake8-lint check
flake8-lint check .
flake8-lint check src tests
```

Exit codes are part of the public contract:

- `0` = completed, no lint violations
- `1` = completed, lint violations found
- `2` = invalid invocation, configuration error, or tool failure

`--output-format` is scaffolded for `text` and `json` output.

## Configuration

`flake8-lint` reads configuration from either `pyproject.toml`:

```toml
[tool.flake8_lint]
include = []
exclude = []
select = []
ignore = []
allow_noqa = true
noqa_allowed = []
noqa_forbidden = []
rule_modules = []
```

or `flake8_lint.toml`:

```toml
include = []
exclude = []
select = []
ignore = []
allow_noqa = true
noqa_allowed = []
noqa_forbidden = []
rule_modules = []
```

Legacy `[tool.flake8_lint_tests]` remains a migration bridge for the copied implementation.

## Built-in rules

The built-in registry reserves and catalogs these rule codes:

- `X001`
- `X002`
- `X003` (reserved/disabled)
- `X004`
- `X005`
- `X006`
- `X007`
- `X008`
- `X009`
- `X010`
- `X011`
- `X012`

## Custom rules

Custom rules are first-class and execute through the same registry and engine as built-in rules.

Supported extension mechanisms:

1. project-local modules configured via `rule_modules`
2. installed providers exposed through the `flake8_lint.rules` entry-point group

See [docs/custom-rules.md](docs/custom-rules.md) for the public contract.

## Flake8 integration

The Flake8 entry point is intentionally thin and adapts Flake8's AST plugin surface to the shared engine. Task 0001 keeps external custom-provider support authoritative in the standalone engine and CLI instead of over-promising Flake8-side discovery behavior.

## pytest integration

Pytest integration is explicit opt-in:

```python
from flake8_lint.testing import assert_lint_clean


def test_project_lint() -> None:
    assert_lint_clean()
```

Installing `flake8-lint` must not cause ordinary `pytest` runs in consuming projects to lint the repository automatically.

## Migration from copied source

The copied implementation used the `flake8_project_rules` namespace. This repository establishes `flake8_lint` as the canonical package namespace while preserving the current X-rule catalogue and reserved `X003` semantics.

## Development

```bash
pytest
ruff check .
python -m build
```

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/custom-rules.md](docs/custom-rules.md)
