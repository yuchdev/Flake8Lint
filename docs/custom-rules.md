# Custom Rules

Use a custom rule when a project needs additional AST checks beyond the built-in X001–X014 catalogue.

## Supported public imports

Import from the package root:

```python
from flakeforge import RuleContext, RuleRegistry, RuleViolation, check_source, lint_paths
```

These names are the supported extension surface for 1.0.0.

## Rule contract

Custom rules do not need to inherit from a framework base class. A rule object only needs:

- `code`: uppercase alphanumeric prefix plus three digits, such as `ACME001`
- `description`: short human-readable text
- `check(context)`: returns an iterable of `RuleViolation`

Example:

```python
import ast
from collections.abc import Iterable

from flakeforge import RuleContext, RuleViolation


class NoPrintRule:
    code = "ACME001"
    description = "Do not call print() in production code."

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        for node in ast.walk(context.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                yield RuleViolation(
                    context.filename,
                    node.lineno,
                    node.col_offset,
                    self.code,
                    self.description,
                )
```

## `RuleContext`

`RuleContext` fields:

- `tree`: parsed module AST
- `filename`: filename reported in diagnostics
- `source`: original source text when available, otherwise `None`

The core engine owns `# noqa` processing, so rules should report violations and let the shared engine decide whether they are suppressed.

## `RuleViolation`

`RuleViolation` fields:

- `filename`
- `lineno`
- `col_offset`
- `code`
- `message`

Built-in and custom rules use the same dataclass and the same output formatting.

## Rule-code naming

Custom codes must:

- be uppercase
- start with a non-empty alphabetic/alphanumeric prefix
- end with exactly three decimal digits
- be unique in the resolved registry

Examples:

- valid: `ACME001`, `SEC001`, `ARCH101`
- invalid: `acme001`, `001`, `ACME01`

Duplicate codes are errors, including collisions with built-in `X001`–`X014`.

## Project-local registration

Project-local modules register rules explicitly:

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

Enable the module with config:

```toml
[tool.flakeforge]
rule_modules = ["my_project.lint_rules"]
```

or CLI:

```bash
flakeforge check --rule-module my_project.lint_rules .
```

Module import failures are reported as tool/configuration errors and name the module plus the base directory it was searched from, along with the original exception.

## Trust boundary

Project-local `rule_modules` are Python modules that `flakeforge` **imports and runs**. When the standalone CLI loads a discovered or explicit config, it puts that config's directory first on `sys.path` while those modules import, so a checkout's own rule modules load without the project being installed.

This means running `flakeforge` on a repository executes the code listed in that repository's `rule_modules` (from its `flakeforge.toml` or `pyproject.toml [tool.flakeforge]`), with your user's privileges, at import time. Treat a cloned repository as untrusted input:

- Run `flakeforge check --no-config <path>` on untrusted checkouts. `--no-config` loads **no** project rule modules and never places the target directory on `sys.path`.
- `--rule-module NAME` stays an explicit opt-in. Under `--no-config`, or when no config file is found for the target, it resolves only from the existing `sys.path` (installed packages / `PYTHONPATH`), not from the target directory.
- Installed `flakeforge.rules` entry-point providers are unaffected by this boundary; they resolve through installed package metadata, and `--no-rule-plugins` disables them.

The `base_dir` placed on `sys.path` is always the resolved config directory, never a raw path argument, and it is removed again as soon as the modules finish loading (even if loading fails).

## Installed provider packages

Reusable packages register through the `flakeforge.rules` entry-point group:

```toml
[project.entry-points."flakeforge.rules"]
acme = "acme_flake8_rules:register_rules"
```

The target must be a callable with signature equivalent to:

```python
from flakeforge import RuleRegistry


def register_rules(registry: RuleRegistry) -> None:
    ...
```

Provider loading is deterministic by entry-point name and target. Provider load failures report the provider name and target, plus the underlying exception. For reproducibility or debugging, disable installed providers with:

```bash
flakeforge check --no-rule-plugins .
```

## Shared execution behavior

Built-in and custom rules share:

- the same `RuleRegistry`
- the same `RuleContext` and `RuleViolation`
- deterministic rule ordering
- `select` / `ignore` filtering
- `# noqa` parsing and suppression

Selectors support exact codes and prefixes consistently. For example, `select = ["ACME"]` enables `ACME001`.

## `# noqa` behavior

Custom codes use the same suppression forms as built-ins:

```python
print("debug")  # noqa: ACME001
```

Suppression still depends on global `allow_noqa` plus the `noqa_allowed` / `noqa_forbidden` path policy.

## Direct unit testing

Provider authors can test a rule without a project scan:

```python
from flakeforge import check_source
from flakeforge.config import LintConfig


violations = check_source(
    'print("hello")\n',
    filename="example.py",
    config=LintConfig(select=("ACME001",)),
    rules=[NoPrintRule()],
)

assert [violation.code for violation in violations] == ["ACME001"]
```

## Integration testing with `lint_paths`

To test project-local registration or file discovery:

```python
from pathlib import Path

from flakeforge import lint_paths
from flakeforge.config import LintConfig


result = lint_paths(
    [Path("src")],
    config=LintConfig(
        select=("ACME001",),
        rule_modules=("my_project.lint_rules",),
    ),
)

assert not result.ok
```

## Compatibility expectations

The 1.0.0 public custom-rule API guarantees:

- explicit registration through `RuleRegistry`
- duplicate-code rejection
- shared filtering/noqa semantics
- deterministic standalone CLI/API/provider loading

Not guaranteed through native Flake8 integration:

- automatic loading of `flakeforge.rules` providers inside Flake8 itself
- universal equivalence with arbitrary third-party Flake8 plugin-selection behavior

If a third-party package needs direct Flake8 discovery, it should also expose its own Flake8 entry point.
