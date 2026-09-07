# Custom Rules

Use a custom rule when a project needs additional AST checks beyond the built-in X001–X012 catalogue.

## Supported public imports

Import from the package root:

```python
from flake8_lint import RuleContext, RuleRegistry, RuleViolation, check_source, lint_paths
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

from flake8_lint import RuleContext, RuleViolation


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

Duplicate codes are errors, including collisions with built-in `X001`–`X012`.

## Project-local registration

Project-local modules register rules explicitly:

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

Enable the module with config:

```toml
[tool.flake8_lint]
rule_modules = ["my_project.lint_rules"]
```

or CLI:

```bash
flake8-lint check --rule-module my_project.lint_rules .
```

Module import failures are reported as tool/configuration errors and name the module plus the original exception.

## Installed provider packages

Reusable packages register through the `flake8_lint.rules` entry-point group:

```toml
[project.entry-points."flake8_lint.rules"]
acme = "acme_flake8_rules:register_rules"
```

The target must be a callable with signature equivalent to:

```python
from flake8_lint import RuleRegistry


def register_rules(registry: RuleRegistry) -> None:
    ...
```

Provider loading is deterministic by entry-point name and target. Provider load failures report the provider name and target, plus the underlying exception. For reproducibility or debugging, disable installed providers with:

```bash
flake8-lint check --no-rule-plugins .
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
from flake8_lint import check_source
from flake8_lint.config import LintConfig


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

from flake8_lint import lint_paths
from flake8_lint.config import LintConfig


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

- automatic loading of `flake8_lint.rules` providers inside Flake8 itself
- universal equivalence with arbitrary third-party Flake8 plugin-selection behavior

If a third-party package needs direct Flake8 discovery, it should also expose its own Flake8 entry point.
