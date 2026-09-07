# flake8-lint

Reusable AST-based Python lint rules with a standalone CLI, a thin Flake8 adapter, explicit pytest helpers, and first-class custom-rule support.

## What it is

`flake8-lint` packages the copied `flake8_project_rules` behavior as a reusable distribution:

- standalone `flake8-lint check`
- shared Python API
- built-in X001–X012 rules with reserved `X003`
- project-local and installed custom rules
- opt-in pytest helper
- thin Flake8 integration over the same core engine

## Installation

```bash
pip install flake8-lint
```

For local development:

```bash
pip install -e .[dev]
```

## Basic CLI usage

```bash
flake8-lint --version
flake8-lint check
flake8-lint check .
flake8-lint check src tests
flake8-lint check path/to/file.py
flake8-lint check --select X002 --ignore X011 src
flake8-lint check --output-format json .
flake8-lint check --rule-module my_project.lint_rules .
flake8-lint check --no-rule-plugins .
```

Exit codes:

- `0` = completed, no violations
- `1` = completed, violations found
- `2` = invalid config, invalid invocation, or tool failure

## `pyproject.toml` configuration

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

Legacy `[tool.flake8_lint_tests]` is still accepted as a 1.0.0 migration fallback when the canonical section is absent. The CLI warns:

```text
[tool.flake8_lint_tests] is deprecated; rename it to [tool.flake8_lint].
```

## `flake8_lint.toml` configuration

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

Discovery precedence:

1. `--config PATH`
2. `flake8_lint.toml`
3. `pyproject.toml` with `[tool.flake8_lint]`
4. `pyproject.toml` with `[tool.flake8_lint_tests]`
5. defaults

`include` is a whitelist. `exclude` is a blacklist and wins. `select` is a whitelist. `ignore` is a blacklist and wins. `noqa_allowed` and `noqa_forbidden` are path filters for files allowed to use `# noqa`; `noqa_forbidden` wins.

## Built-in rules

- `X001` bare `except:`
- `X002` `except Exception:`
- `X003` reserved/disabled
- `X004` silently swallowed exceptions
- `X005` missing or malformed docstrings
- `X006` local imports inside functions or classes
- `X007` value-returning functions without return annotations
- `X008` explicit `-> None`
- `X009` old `%` string formatting
- `X010` suppressed `ImportError` / `ModuleNotFoundError`
- `X011` `Type | None` instead of `Optional[Type]`
- `X012` non-`None` PEP 604 unions like `Type1 | Type2` instead of `Union[...]`

## `# noqa` semantics

Supported forms:

```python
# noqa
# noqa: X002
# noqa: X001, X002
# noqa: ACME001
```

- bare `# noqa` suppresses package violations on that line
- code-qualified markers suppress only matching codes or prefixes
- `allow_noqa = false` disables suppression globally
- `noqa_allowed` restricts suppression to matching file paths when non-empty
- `noqa_forbidden` always blocks suppression for matching file paths

If source text is unavailable, the engine still reports violations but cannot apply source-based `# noqa` suppression.

## Custom rules

Minimal project-local registration:

```python
# my_project/lint_rules.py
import ast
from flake8_lint import RuleContext, RuleRegistry, RuleViolation


class NoPrintRule:
    code = "ACME001"
    description = "Do not call print() in production code."

    def check(self, context: RuleContext):
        for node in ast.walk(context.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                yield RuleViolation(
                    context.filename,
                    node.lineno,
                    node.col_offset,
                    self.code,
                    self.description,
                )


def register_rules(registry: RuleRegistry) -> None:
    registry.register(NoPrintRule(), provider="my_project.lint_rules")
```

```toml
[tool.flake8_lint]
rule_modules = ["my_project.lint_rules"]
```

Reusable provider packages can also register through the `flake8_lint.rules` Python entry-point group. See [docs/custom-rules.md](docs/custom-rules.md).

## Flake8 integration

`flake8-lint` registers a Flake8 AST plugin entry point. The adapter is intentionally thin:

- built-in diagnostics come from the same shared engine used by the CLI/API
- Flake8 selection and `--disable-noqa` map into the shared engine
- installed `flake8_lint.rules` providers remain authoritative for the standalone CLI/API
- third-party packages that need native Flake8 discovery should also expose their own Flake8 entry points

## pytest integration

Pytest integration is explicit:

```python
from flake8_lint.testing import assert_lint_clean


def test_project_lint() -> None:
    assert_lint_clean("src", "tests")
```

Installing `flake8-lint` alone does not auto-run repository lint during ordinary `pytest`.

## CI recommendation

Prefer separate steps or jobs:

```bash
flake8-lint check .
pytest
```

That keeps unit and integration tests running even when lint finds violations.

## Migration from the copied implementation

Before:

```text
src/flake8_project_rules/
tests/flake8_lint/config.py
tests/flake8_lint/test_plugin_direct.py
tests/flake8_lint/test_project_lint.py
tests/flake8_lint/samples/
```

Add dependency:

```text
flake8-lint==1.0.0
```

Then:

- remove `src/flake8_project_rules/`
- remove copied package-implementation tests now owned by `flake8-lint`
- remove `test_project_lint.py` unless pytest should stay an explicit lint gate
- rename `[tool.flake8_lint_tests]` to `[tool.flake8_lint]`
- change CI from implicit pytest lint gating to:

```bash
flake8-lint check .
pytest
```

- update direct imports from `flake8_project_rules` to public `flake8_lint` APIs where needed

## Canonical migrated configuration example

`pyproject.toml`:

```toml
[tool.flake8_lint]

include = []

exclude = [
    "tests/flake8_lint/samples/",
    "src/aegis_swr/openclaude/grpc/client.py",
    "src/aegis_swr/openclaude/tool.py",
    "src/aegis_swr/openclaude/grpc/proto/",
    "src/aegis_swr/openhands/client.py",
    "src/aegis_swr/openhands/tool.py",
    "src/aegis_swr/claude_code/tool.py",
]

select = [
    "X001",
    "X002",
    "X004",
    "X005",
    "X006",
    "X007",
    "X008",
    "X009",
    "X010",
    "X011",
    "X012",
]

ignore = ["X003"]

allow_noqa = true

noqa_allowed = [
    "src/aegis_swr/core/events.py",
]

noqa_forbidden = []

rule_modules = []
```

Equivalent `flake8_lint.toml`:

```toml
include = []

exclude = [
    "tests/flake8_lint/samples/",
    "src/aegis_swr/openclaude/grpc/client.py",
    "src/aegis_swr/openclaude/tool.py",
    "src/aegis_swr/openclaude/grpc/proto/",
    "src/aegis_swr/openhands/client.py",
    "src/aegis_swr/openhands/tool.py",
    "src/aegis_swr/claude_code/tool.py",
]

select = [
    "X001",
    "X002",
    "X004",
    "X005",
    "X006",
    "X007",
    "X008",
    "X009",
    "X010",
    "X011",
    "X012",
]

ignore = ["X003"]
allow_noqa = true
noqa_allowed = ["src/aegis_swr/core/events.py"]
noqa_forbidden = []
rule_modules = []
```

## Development / build

```bash
pytest --cov=flake8_lint --cov-report=term-missing
ruff check .
python -m build
```

Additional documentation:

- [docs/custom-rules.md](docs/custom-rules.md)
- [docs/architecture.md](docs/architecture.md)
