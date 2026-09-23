# flakeforge

Reusable AST-based Python lint rules with a standalone CLI, a thin Flake8 adapter, explicit pytest helpers, and first-class custom-rule support.

> Formerly `flake8-lint`. Renamed to `flakeforge` to read as an extension of Flake8 rather than
> Flake8 itself — see the [migration note](#renamed-from-flake8-lint) below.

## What it is

`flakeforge` packages the copied `flake8_project_rules` behavior as a reusable distribution:

- standalone `flakeforge check`
- shared Python API
- built-in X001–X014 rules, all enabled by default
- project-local and installed custom rules
- opt-in pytest helper
- thin Flake8 integration over the same core engine

## Installation

```bash
pip install flakeforge
```

For local development:

```bash
pip install -e .[dev]
```

## Basic CLI usage

```bash
flakeforge --version
flakeforge check
flakeforge check .
flakeforge check src tests
flakeforge check path/to/file.py
flakeforge check --select X002 --ignore X011 src
flakeforge check --output-format json .
flakeforge check --rule-module my_project.lint_rules .
flakeforge check --no-rule-plugins .
```

Exit codes:

- `0` = completed, no violations
- `1` = completed, violations found
- `2` = invalid config, invalid invocation, or tool failure

## `pyproject.toml` configuration

```toml
[tool.flakeforge]
include = []
exclude = []
select = []
ignore = []
allow_noqa = true
noqa_allowed = []
noqa_forbidden = []
rule_modules = []
```

Legacy `[tool.flake8_lint]` is still accepted as a migration fallback when the canonical section
is absent — the same way `[tool.flake8_lint_tests]` was accepted as a fallback for
`[tool.flake8_lint]` before this rename (that older fallback is now retired). The CLI warns:

```text
[tool.flake8_lint] is deprecated; rename it to [tool.flakeforge].
```

## `flakeforge.toml` configuration

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
2. `flakeforge.toml`
3. `pyproject.toml` with `[tool.flakeforge]`
4. `pyproject.toml` with `[tool.flake8_lint]` (deprecated)
5. defaults

`include` is a whitelist. `exclude` is a blacklist and wins. `select` is a whitelist. `ignore` is a blacklist and wins. `noqa_allowed` and `noqa_forbidden` are path filters for files allowed to use `# noqa`; `noqa_forbidden` wins.

## Built-in rules

- `X001` bare `except:`
- `X002` `except Exception:`
- `X003` circular imports between project modules
- `X004` silently swallowed exceptions
- `X005` missing or malformed docstrings
- `X006` local imports inside functions or classes
- `X007` value-returning functions without return annotations
- `X008` explicit `-> None`
- `X009` old `%` string formatting
- `X010` suppressed `ImportError` / `ModuleNotFoundError`
- `X011` `Type | None` instead of `Optional[Type]`
- `X012` non-`None` PEP 604 unions like `Type1 | Type2` instead of `Union[...]`
- `X013` `subprocess.Popen`/`socket.socket` not used as a context manager
- `X014` malformed or untracked `TODO`/`FIXME` comments

### `X003` circular imports

`X003` resolves each module's runtime imports against its import root - the first directory above the module that is not a package - and reports any import that takes part in a cycle leading back to the module being checked. Every module in a cycle is flagged, each at its own offending import line, and the message names the full chain:

```text
src/pkg/alpha.py:3:0: X003 Circular import detected: pkg.alpha -> pkg.beta -> pkg.alpha; ...
```

These are deliberately *not* treated as cycle edges, because Python does not run them while first importing the module:

- imports inside a function body, which is the standard way to break a cycle
- imports guarded by `if TYPE_CHECKING:`
- targets that do not resolve to a file under the import root, so the standard library and third-party packages are never traversed

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
from flakeforge import RuleContext, RuleRegistry, RuleViolation


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
[tool.flakeforge]
rule_modules = ["my_project.lint_rules"]
```

Reusable provider packages can also register through the `flakeforge.rules` Python entry-point group. See [docs/custom-rules.md](docs/custom-rules.md).

## Flake8 integration

`flakeforge` registers a Flake8 AST plugin entry point. The adapter is intentionally thin:

- built-in diagnostics come from the same shared engine used by the CLI/API
- Flake8 selection and `--disable-noqa` map into the shared engine
- installed `flakeforge.rules` providers remain authoritative for the standalone CLI/API
- third-party packages that need native Flake8 discovery should also expose their own Flake8 entry points

## pytest integration

Pytest integration is explicit:

```python
from flakeforge.testing import assert_lint_clean


def test_project_lint() -> None:
    assert_lint_clean("src", "tests")
```

Installing `flakeforge` alone does not auto-run repository lint during ordinary `pytest`.

## CI recommendation

Prefer separate steps or jobs:

```bash
flakeforge check .
pytest
```

That keeps unit and integration tests running even when lint finds violations.

## Renamed from flake8-lint

This project was initially released as `flake8-lint` and was later renamed to `flakeforge` to
avoid it reading as "flake8 itself" rather than an extension of it.
If you depend on an older release or a pre-rename commit:

- the import package is `flakeforge` (was `flake8_lint`)
- the console script is `flakeforge` (was `flake8-lint`)
- the canonical config section is `[tool.flakeforge]` / `flakeforge.toml` (was `[tool.flake8_lint]` /
  `flake8_lint.toml`) — `[tool.flake8_lint]` is still accepted as a deprecated fallback, same as
  any other config migration (see the precedence list above)
- the custom-rule entry-point group is `flakeforge.rules` (was `flake8_lint.rules`)

No rule code, rule behaviour, or public API shape changed - only names.

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
flakeforge==1.0.0
```

Then:

- remove `src/flake8_project_rules/`
- remove copied package-implementation tests now owned by `flakeforge`
- remove `test_project_lint.py` unless pytest should stay an explicit lint gate
- rename the legacy config section to `[tool.flakeforge]`
- change CI from implicit pytest lint gating to:

```bash
flakeforge check .
pytest
```

- update direct imports from `flake8_project_rules` to public `flakeforge` APIs where needed

## Canonical migrated configuration example

`pyproject.toml`:

```toml
[tool.flakeforge]

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
    "X003",
    "X004",
    "X005",
    "X006",
    "X007",
    "X008",
    "X009",
    "X010",
    "X011",
    "X012",
    "X013",
    "X014",
]

ignore = []

allow_noqa = true

noqa_allowed = [
    "src/aegis_swr/core/events.py",
]

noqa_forbidden = []

rule_modules = []
```

Equivalent `flakeforge.toml`:

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
    "X003",
    "X004",
    "X005",
    "X006",
    "X007",
    "X008",
    "X009",
    "X010",
    "X011",
    "X012",
    "X013",
    "X014",
]

ignore = []
allow_noqa = true
noqa_allowed = ["src/aegis_swr/core/events.py"]
noqa_forbidden = []
rule_modules = []
```

## Development / build

```bash
pytest --cov=flakeforge --cov-report=term-missing
ruff check .
python -m build
```

Additional documentation:

- [docs/custom-rules.md](docs/custom-rules.md)
- [docs/architecture.md](docs/architecture.md)
